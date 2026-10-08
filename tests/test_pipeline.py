"""Correctness tests include hand-counted baskets, edge cases and real-data checks."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from mlxtend.preprocessing import TransactionEncoder
from src.pipeline import (ROOT,RAW,AnalysisConfig,RuleFilter,load_raw,audit,clean,encode,mine,filter_rules,is_disease_rule,run_pipeline)

@pytest.fixture(scope='module')
def real():
    raw=load_raw(); frame,log=clean(raw); transactions,matrix,mapping=encode(frame,raw)
    return raw,frame,log,transactions,matrix,mapping

def test_source_identity_and_loading(real,tmp_path):
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()=='79cd5314cfdefec9b86ee0efd63d3df64a619a2e2511c5908abde008edf1bfa8'
    assert real[0].shape==(349,10)
    with pytest.raises(FileNotFoundError): load_raw(tmp_path/'absent.csv')

def test_audit_and_cleaning(real):
    q=audit(real[0]); assert q['duplicate_rows']==49 and q['missing_values']==0
    assert len(real[1])==300 and real[2]['duplicate_rows_removed']==49
    assert q['numerical_columns']==['Age'] and len(q['suspicious_values'])>=1
    assert real[1]['Disease'].nunique()==116
    assert len(clean(real[0],False)[0])==349

@pytest.mark.parametrize('value',['','?','NA','N/A','null','Unknown','unavailable','malformed'])
def test_missing_or_invalid_symptoms_never_mean_no(real,value):
    raw=real[0].head(1).copy(); raw.loc[0,'Fever']=value
    frame,log=clean(raw); tx,matrix,_=encode(frame)
    assert frame.loc[0,'Fever']=='Unknown'
    assert not any(x.startswith('Fever=') for x in tx[0])

def test_normalization_and_explicit_absence(real):
    raw=real[0].head(1).copy(); raw.loc[0,'Fever']=' yEs '; raw.loc[0,'Cough']='0'
    frame,_=clean(raw); tx,_,_=encode(frame)
    assert 'Fever=Yes' in tx[0] and 'Cough=No' in tx[0]

@pytest.mark.parametrize('age,group',[(0,'0-17'),(17,'0-17'),(18,'18-30'),(30,'18-30'),(31,'31-45'),(45,'31-45'),(46,'46-60'),(60,'46-60'),(61,'61+'),(120,'61+'),(-1,'Unknown'),(121,'Unknown'),(20.5,'Unknown'),('bad','Unknown')])
def test_age_boundaries(real,age,group):
    raw=real[0].head(1).copy(); raw.loc[0,'Age']=str(age)
    frame,_=clean(raw); assert frame.loc[0,'Age_Group']==group

def test_encoding_transactions_and_metadata(real):
    _,frame,_,tx,matrix,mapping=real
    assert len(tx)==300 and matrix.shape[0]==300
    assert matrix.dtypes.eq(bool).all()
    assert all(t and len(t)==len(set(t)) for t in tx)
    assert all('=' in i and not i.endswith('=Unknown') for t in tx for i in t)
    assert not any(i.startswith(('Outcome_Variable=','Age=')) for t in tx for i in t)
    assert {x['original_column'] for x in mapping}==set(real[0].columns)
    for idx,row in enumerate(tx): assert set(matrix.columns[matrix.iloc[idx]])==set(row)

def test_hand_counted_apriori_metrics():
    # Deliberately synthetic UNIT TEST baskets, never included in project data/results.
    tx=[['A=Yes','Disease=X'],['A=Yes','Disease=X'],['A=Yes','Disease=Y'],['B=Yes','Disease=Y']]
    te=TransactionEncoder(); matrix=pd.DataFrame(te.fit_transform(tx),columns=te.columns_)
    itemsets,rules,disease,_=mine(matrix,AnalysisConfig(min_support=.25,min_confidence=0,min_lift=0,max_itemset_size=3))
    r=next(r for r in disease if r['antecedents']==['A=Yes'] and r['consequents']==['Disease=X'])
    assert r['support']==.5
    assert r['confidence']==pytest.approx(2/3)
    assert r['lift']==pytest.approx(4/3)
    assert r['leverage']==pytest.approx(.125)
    assert r['conviction']==pytest.approx(1.5)
    assert next(x for x in itemsets if x['itemset']==['A=Yes'])['item_count']==3

def test_actual_metrics_independently_counted(real):
    _,_,_,tx,matrix,_=real
    itemsets,rules,disease,counts=mine(matrix,AnalysisConfig())
    assert (len(itemsets),len(rules),len(disease))==(2209,3826,12)
    assert all(is_disease_rule(r) for r in disease)
    keys=[(tuple(r['antecedents']),tuple(r['consequents'])) for r in rules]
    assert len(keys)==len(set(keys))
    for r in rules:
        assert set(r['antecedents']).isdisjoint(r['consequents'])
        assert 0<=r['support']<=1 and 0<=r['confidence']<=1 and r['lift']>=0
        assert all(v is None or not isinstance(v,float) or np.isfinite(v) for v in r.values())
        a=matrix[r['antecedents']].all(axis=1); b=matrix[r['consequents']].all(axis=1)
        assert r['support']==pytest.approx((a&b).mean())
        assert r['confidence']==pytest.approx((a&b).sum()/a.sum())
        assert r['lift']==pytest.approx(r['confidence']/b.mean())

def test_filters_and_caps(real):
    _,rules,disease,_=mine(real[4],AnalysisConfig())
    f=RuleFilter(disease='Asthma',min_lift=2,top_n=3,max_antecedent_length=3,disease_only=True)
    filtered=filter_rules(rules,f)
    assert len(filtered['items'])<=3 and all(r['consequents']==['Disease=Asthma'] for r in filtered['items'])
    assert filter_rules(rules,RuleFilter(search='not-a-real-item'))['total']==0
    _,capped,dc,counts=mine(real[4],AnalysisConfig(max_rules=1))
    assert len(capped)==1 and len(dc)==1 and counts['disease_rules_before_cap']==12

def test_empty_result_safely_serializable(real):
    itemsets,rules,disease,_=mine(real[4],AnalysisConfig(min_support=1))
    assert not rules and not disease
    json.dumps({'rules':rules,'itemsets':itemsets},allow_nan=False)

def test_reproducible_outputs_and_raw_preservation(tmp_path):
    before=RAW.read_bytes(); a=run_pipeline(root=tmp_path/'first'); b=run_pipeline(root=tmp_path/'second')
    a['summary'].pop('generated_at'); b['summary'].pop('generated_at')
    assert a==b and RAW.read_bytes()==before
    for file in ['frequent_itemsets.csv','association_rules.csv','disease_rules.csv','preprocessing_metadata.json']:
        assert (tmp_path/'first/results'/file).read_bytes()==(tmp_path/'second/results'/file).read_bytes()
