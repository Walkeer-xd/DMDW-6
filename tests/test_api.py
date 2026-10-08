import json
import pytest
from fastapi.testclient import TestClient
from backend.app import main
from src.pipeline import ROOT

@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(main,'state',json.loads((ROOT/'results/analysis.json').read_text(encoding='utf-8')))
    return TestClient(main.app)

@pytest.mark.parametrize('endpoint',['health','analysis','dataset/summary','dataset/columns','dataset/missing-values','dataset/distribution','apriori/itemsets','apriori/rules','apriori/rules/disease','apriori/top-rules','apriori/metrics'])
def test_get_responses(client,endpoint):
    r=client.get('/api/'+endpoint); assert r.status_code==200
    json.dumps(r.json(),allow_nan=False)

@pytest.mark.parametrize('body',[{'min_support':0},{'min_confidence':1.1},{'max_itemset_size':10},{'max_rules':0},{'unexpected':1}])
def test_parameter_validation(client,body): assert client.post('/api/apriori/run',json=body).status_code==422

def test_filter_validation_and_exact_disease(client):
    assert client.get('/api/apriori/rules?min_support=-1').status_code==422
    assert client.get('/api/apriori/rules?sort_by=invalid').status_code==422
    r=client.post('/api/apriori/filter',json={'disease_only':True,'disease':'Asthma','top_n':2}).json()
    assert len(r['items'])<=2 and all(x['consequents']==['Disease=Asthma'] for x in r['items'])

@pytest.mark.parametrize('kind',['rules','all-rules','disease-rules','itemsets','cleaned','analysis','report','pdf'])
def test_export(client,kind):
    r=client.get('/api/export/'+kind); assert r.status_code==200 and len(r.content)>20
    assert 'attachment' in r.headers['content-disposition']

def test_empty_export_and_unknown_route(client):
    r=client.get('/api/export/rules?search=not-a-real-item')
    assert r.status_code==200 and 'antecedents' in r.text
    assert client.get('/api/export/not-an-export').status_code==404

def test_concurrent_run_rejected(client):
    main.lock.acquire()
    try: assert client.post('/api/apriori/run',json={}).status_code==409
    finally: main.lock.release()

def test_successful_run_isolated_from_delivery(client,tmp_path,monkeypatch):
    monkeypatch.setattr(main,'ROOT',tmp_path)
    r=client.post('/api/apriori/run',json={'min_support':.1,'max_itemset_size':2})
    assert r.status_code==200
    assert (tmp_path/'reports/DMDW6_Report.pdf').exists()
    assert client.get('/api/analysis').json()['config']['min_support']==.1
    assert json.loads((tmp_path/'results/analysis.json').read_text(encoding='utf-8'))['summary']==r.json()['summary']
