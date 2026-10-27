"""Exercise temporary uploads against the real pipelines and independently counted rules."""
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile

from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from backend.app import upload_demo

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.parametrize('kind', ['profiles', 'symptoms'])
def test_samples_run_and_leave_saved_data_untouched(client, kind, monkeypatch, tmp_path):
    protected = [p for folder in ['results', 'data', 'datasets']
                 for p in (ROOT / folder).rglob('*') if p.is_file()]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    directories = []
    original = tempfile.TemporaryDirectory

    def temporary(**kwargs):
        directory = original(dir=tmp_path, **kwargs)
        directories.append(Path(directory.name))
        return directory

    monkeypatch.setattr(upload_demo.tempfile, 'TemporaryDirectory', temporary)
    sample = client.get(f'/api/demo/sample/{kind}')
    assert sample.status_code == 200
    assert 'attachment' in sample.headers['content-disposition']
    response = client.post('/api/demo/analyze', content=sample.content, headers={'Content-Type': 'text/csv'})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    events = [json.loads(line) for line in response.text.splitlines()]
    assert [e['step'] for e in events if e['type'] == 'step'] == [
        'validate', 'read', 'audit', 'clean', 'encode', 'itemsets', 'results']
    assert events[-1]['type'] == 'complete'
    result = events[-1]
    a = result['analysis']
    assert a['summary']['raw_records'] == 63
    assert a['summary']['records'] == 60
    assert a['cleaning']['duplicate_rows_removed'] == 3
    assert a['summary']['disease_classes'] == 3
    assert a['disease_rules']
    baskets = [set(json.loads(row['items'])) for row in
               csv.DictReader(io.StringIO(result['artifacts']['transactions']))]
    for rule in a['disease_rules']:
        left, right = set(rule['antecedents']), set(rule['consequents'])
        both = sum((left | right) <= row for row in baskets)
        left_count = sum(left <= row for row in baskets)
        right_count = sum(right <= row for row in baskets)
        assert rule['support'] == pytest.approx(both / len(baskets))
        assert rule['confidence'] == pytest.approx(both / left_count)
        assert rule['lift'] == pytest.approx((both / left_count) / (right_count / len(baskets)))
    assert directories and all(not p.exists() for p in directories)
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}


def test_duplicate_policy_and_empty_rules(client):
    sample = client.get('/api/demo/sample/profiles').content
    r = client.post('/api/demo/analyze?remove_duplicates=false&min_support=1&min_lift=1000', content=sample)
    result = json.loads(r.text.splitlines()[-1])['analysis']
    assert result['summary']['records'] == 63
    assert result['rules'] == []


@pytest.mark.parametrize('body', [b'', b'Disease,Symptom_1\nDemo,cough', b'a,a\nx,y',
                                  b'a,b\nx', b'\xff\x00', b'a,b\nx,"unterminated'])
def test_invalid_upload_rejected(client, body):
    assert client.post('/api/demo/analyze', content=body).status_code == 400


def test_upload_limits_and_parameters(client):
    assert client.post('/api/demo/analyze', content=b'x' * 1_000_001).status_code == 413
    sample = client.get('/api/demo/sample/profiles').content
    assert client.post('/api/demo/analyze?min_support=0.001', content=sample).status_code == 422
    assert client.get('/api/demo/sample/unknown').status_code == 404
    rows = sample.decode().splitlines()
    assert client.post('/api/demo/analyze', content='\n'.join([rows[0], *[rows[1]] * 1001])).status_code == 400


def test_conflicting_demo_rejected(client):
    upload_demo.demo_lock.acquire()
    try:
        sample = client.get('/api/demo/sample/profiles').content
        assert client.post('/api/demo/analyze', content=sample).status_code == 409
    finally:
        upload_demo.demo_lock.release()


def test_failed_pipeline_cleans_temp_files_and_releases_lock(client, monkeypatch, tmp_path):
    original = tempfile.TemporaryDirectory
    monkeypatch.setattr(upload_demo.tempfile, 'TemporaryDirectory', lambda **kw: original(dir=tmp_path, **kw))

    def fail(*args, **kwargs):
        raise ValueError('Deliberate invalid dataset')

    monkeypatch.setattr(upload_demo, 'run_pipeline', fail)
    sample = client.get('/api/demo/sample/profiles').content
    response = client.post('/api/demo/analyze', content=sample)
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1] == {'type': 'error', 'message': 'Deliberate invalid dataset'}
    assert not upload_demo.demo_lock.locked()
    assert list(tmp_path.iterdir()) == []
