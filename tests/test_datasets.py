"""Dataset selection, semantic adaptation, and cross-source isolation."""
import hashlib
import io
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from src.datasets import DATASETS, dataset_root, dataset_spec
from src.pipeline import ROOT, AnalysisConfig, load_raw
from src.symptom_pipeline import prepare_symptoms, run_symptom_pipeline

SYMPTOM_ROOT = ROOT / 'datasets/symptoms'
SYMPTOM_RAW = SYMPTOM_ROOT / 'data/raw/dataset.csv'


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(main, 'state', None)
    monkeypatch.setattr(main, 'dataset_states', {})
    monkeypatch.setattr(main, 'SERVERLESS', False)
    return TestClient(main.app)


def test_source_identity_and_preserved_semantics():
    manifest = json.loads((SYMPTOM_ROOT / 'data/raw/provenance.json').read_text())
    assert hashlib.sha256(SYMPTOM_RAW.read_bytes()).hexdigest() == manifest['sha256']
    raw = load_raw(SYMPTOM_RAW)
    cleaned, quality, log, tx, matrix, mapping, distributions = prepare_symptoms(raw)
    assert raw.shape == (4920, 18)
    assert len(cleaned) == 304 and log['duplicate_rows_removed'] == 4616
    assert len(distributions['Disease']) == 41
    assert len(distributions['Recorded_symptoms']) == 131
    assert not {'Age', 'Gender', 'Blood_Pressure', 'Cholesterol_Level'} & set(cleaned)
    assert all(item.endswith('=Yes') or item.startswith('Disease=') for basket in tx for item in basket)
    assert all(sum(item.startswith('Disease=') for item in basket) == 1 for basket in tx)
    assert all(len(basket) == len(set(basket)) for basket in tx)
    assert matrix.dtypes.eq(bool).all()
    assert sum(distributions['Symptoms_per_profile'].values()) == 304
    assert not any(item.endswith('=No') for item in matrix.columns)
    assert quality['filename'] == 'dataset.csv'
    assert len(prepare_symptoms(raw, False)[0]) == 4920


def test_symptom_schema_and_no_symptom_rejected():
    raw = load_raw(SYMPTOM_RAW).head(1).copy()
    with pytest.raises(ValueError, match='Expected Disease'):
        prepare_symptoms(raw.drop(columns='Symptom_17'))
    raw.loc[:, 'Disease'] = ''
    with pytest.raises(ValueError, match='disease label'):
        prepare_symptoms(raw)
    raw.loc[:, 'Disease'] = 'Recorded test label'
    for slot in raw.columns[1:]:
        raw.loc[:, slot] = ''
    with pytest.raises(ValueError, match='at least one'):
        prepare_symptoms(raw)


def test_symptom_snapshot_and_independently_counted_rules():
    result = json.loads((SYMPTOM_ROOT / 'results/analysis.json').read_text())
    assert result['summary']['records'] == 304
    assert result['summary']['disease_rules'] == 1166
    assert len({row['consequents'][0] for row in result['disease_rules']}) == 40
    assert result['config'] == dataset_spec('symptoms')['default_config']
    transactions = json.loads((SYMPTOM_ROOT / 'data/intermediate/transactions.json').read_text())
    baskets = [set(basket) for basket in transactions]
    for rule in result['disease_rules']:
        left, right = set(rule['antecedents']), set(rule['consequents'])
        both = sum((left | right) <= basket for basket in baskets)
        left_count = sum(left <= basket for basket in baskets)
        right_count = sum(right <= basket for basket in baskets)
        assert rule['item_count'] == both
        assert rule['support'] == pytest.approx(both / len(baskets))
        assert rule['confidence'] == pytest.approx(both / left_count)
        assert rule['lift'] == pytest.approx((both / left_count) / (right_count / len(baskets)))


def test_source_defaults_and_catalog(client):
    catalog = client.get('/api/datasets').json()
    assert catalog['default'] == 'profiles' and catalog['can_run']
    assert {row['id'] for row in catalog['datasets']} == {'profiles', 'symptoms'}
    assert all(row['ready'] for row in catalog['datasets'])
    assert DATASETS['profiles']['default_config']['min_support'] == .02
    assert DATASETS['symptoms']['default_config']['min_support'] == .01
    assert DATASETS['symptoms']['default_config']['max_itemset_size'] == 3
    assert DATASETS['profiles']['has_demographics']
    assert not DATASETS['symptoms']['has_demographics']


@pytest.mark.parametrize('dataset_id', ['profiles', 'symptoms'])
@pytest.mark.parametrize('endpoint', ['analysis', 'dataset/summary', 'dataset/columns', 'dataset/missing-values',
                                     'dataset/distribution', 'apriori/itemsets', 'apriori/rules',
                                     'apriori/rules/disease', 'apriori/top-rules', 'apriori/metrics'])
def test_scoped_reads(client, dataset_id, endpoint):
    response = client.get(f'/api/datasets/{dataset_id}/{endpoint}')
    assert response.status_code == 200, response.text[:500]
    json.dumps(response.json(), allow_nan=False)
    assert len(response.content) < 4_500_000


def test_switching_reads_never_replaces_default_state(client):
    baseline = client.get('/api/analysis').json()
    extended = client.get('/api/datasets/symptoms/analysis').json()
    assert baseline['dataset']['id'] == 'profiles'
    assert extended['dataset']['id'] == 'symptoms'
    assert len(baseline['disease_rules']) == 12
    assert len(extended['disease_rules']) == 1166
    assert client.get('/api/datasets/profiles/analysis').json() == baseline
    assert client.get('/api/analysis').json() == baseline
    assert client.get('/api/datasets/symptoms/analysis').json() == extended


@pytest.mark.parametrize('kind', ['all-rules', 'disease-rules', 'itemsets', 'cleaned', 'analysis', 'report', 'pdf'])
def test_scoped_exports(client, kind):
    response = client.get(f'/api/datasets/symptoms/export/{kind}')
    assert response.status_code == 200
    assert 'symptoms_' in response.headers['content-disposition']
    assert 20 < len(response.content) < 4_500_000
    if kind == 'report':
        assert 'itachi9604' in response.text
        assert 'No age, gender' in response.text
        assert 'uom190346a' not in response.text
    if kind == 'cleaned':
        assert 'Symptom_17' in response.text.splitlines()[0]
        assert 'Age' not in response.text.splitlines()[0]


def test_scoped_filters_csv_and_validation(client):
    base = '/api/datasets/symptoms'
    response = client.get(base + '/apriori/rules/disease?disease=Dengue&top_n=3')
    assert response.status_code == 200, response.text
    assert response.json()['total'] > 0
    assert all(row['consequents'] == ['Disease=Dengue'] for row in response.json()['items'])
    selected = client.post(base + '/apriori/filter', json={'disease_only': True, 'disease': 'Malaria', 'top_n': 2})
    assert selected.status_code == 200 and selected.json()['total'] > 0
    csv = client.get(base + '/export/rules?disease_only=true&disease=Dengue&top_n=3').text
    rows = pd.read_csv(io.StringIO(csv))
    assert len(rows) == 3
    assert all(json.loads(value) == ['Disease=Dengue'] for value in rows['consequents'])
    assert client.get(base + '/apriori/rules?min_support=-1').status_code == 422
    assert client.get(base + '/apriori/rules?sort_by=bad').status_code == 422
    assert client.post(base + '/apriori/run', json={'max_itemset_size': 4}).status_code == 422


def test_unknown_dataset_cannot_address_files(client):
    for endpoint in ['analysis', 'export/analysis', 'apriori/rules']:
        assert client.get('/api/datasets/not-a-source/' + endpoint).status_code == 404
    assert client.post('/api/datasets/not-a-source/apriori/run', json={}).status_code == 404
    with pytest.raises(ValueError):
        dataset_root(ROOT, '../profiles')


def test_new_run_and_exports_are_isolated(client, tmp_path, monkeypatch):
    source = dataset_root(tmp_path, 'symptoms') / 'data/raw/dataset.csv'
    source.parent.mkdir(parents=True)
    shutil.copyfile(SYMPTOM_RAW, source)
    original_json = (ROOT / 'results/analysis.json').read_bytes()
    (tmp_path / 'results').mkdir()
    (tmp_path / 'results/analysis.json').write_bytes(original_json)
    (tmp_path / 'REPORT.md').write_text('Original report sentinel')
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    before = client.get('/api/analysis').json()
    response = client.post('/api/datasets/symptoms/apriori/run', json={'min_support': .1, 'max_itemset_size': 2})
    assert response.status_code == 200, response.text
    assert response.json()['dataset_id'] == 'symptoms'
    assert client.get('/api/analysis').json() == before
    assert (tmp_path / 'results/analysis.json').read_bytes() == original_json
    assert (tmp_path / 'REPORT.md').read_text() == 'Original report sentinel'
    output = dataset_root(tmp_path, 'symptoms')
    assert (output / 'reports/DMDW6_Report.pdf').exists()
    assert json.loads((output / 'results/analysis.json').read_text())['config']['min_support'] == .1
    assert client.get('/api/datasets/symptoms/analysis').json()['config']['min_support'] == .1
    assert client.get('/api/datasets/symptoms/export/pdf').status_code == 200
    assert source.read_bytes() == SYMPTOM_RAW.read_bytes()


def test_failed_run_does_not_publish_a_partial_snapshot(client, monkeypatch):
    before = client.get('/api/datasets/symptoms/analysis').json()
    def fail(*args, **kwargs):
        raise ValueError('Rejected test input')
    monkeypatch.setattr(main, 'run_symptom_pipeline', fail)
    response = client.post('/api/datasets/symptoms/apriori/run', json=before['config'])
    assert response.status_code == 400
    assert client.get('/api/datasets/symptoms/analysis').json() == before
    assert not main.lock.locked()


def test_hosted_mode_and_shared_run_lock(client, monkeypatch):
    main.lock.acquire()
    try:
        assert client.post('/api/datasets/symptoms/apriori/run', json=DATASETS['symptoms']['default_config']).status_code == 409
    finally:
        main.lock.release()
    monkeypatch.setattr(main, 'SERVERLESS', True)
    assert not client.get('/api/datasets').json()['can_run']
    for source in DATASETS:
        assert client.get(f'/api/datasets/{source}/analysis').status_code == 200
        assert client.post(f'/api/datasets/{source}/apriori/run', json=DATASETS[source]['default_config']).status_code == 501


def test_omitted_run_settings_use_selected_source_defaults(client, monkeypatch):
    received = []
    def capture(config, **kwargs):
        received.append(config.model_dump())
        raise ValueError('Stop after inspecting selected defaults')
    monkeypatch.setattr(main, 'run_symptom_pipeline', capture)
    response = client.post('/api/datasets/symptoms/apriori/run', json={})
    assert response.status_code == 400
    assert received == [DATASETS['symptoms']['default_config']]


def test_selected_condition_filters_and_csv_match_exactly(client):
    base = '/api/datasets/symptoms'
    response = client.get(base + '/apriori/rules/disease', params={'item': 'skin_rash=Yes', 'top_n': 100000})
    assert response.status_code == 200
    selected = response.json()
    assert selected['total'] > 0
    assert all('skin_rash=Yes' in row['antecedents'] + row['consequents'] for row in selected['items'])
    exported = client.get(base + '/export/rules', params={'item': 'skin_rash=Yes', 'disease_only': True, 'top_n': 100000})
    rows = pd.read_csv(io.StringIO(exported.text))
    assert len(rows) == selected['total']
    assert client.get(base + '/apriori/rules/disease', params={'item': 'skin_rash'}).json()['total'] == 0
    assert client.post(base + '/apriori/filter', json={'item': 'skin_rash=Yes', 'disease_only': True}).json()['total'] == selected['total']
