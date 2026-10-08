"""Local single-user FastAPI service with atomic result publication."""
from pathlib import Path
import csv
import io
import json
import os
import sys
import threading
import tempfile
import shutil
from typing import Annotated

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from src.pipeline import AnalysisConfig, RuleFilter, filter_rules, run_pipeline

app=FastAPI(title='DMDW6 Apriori API',version='1.0.0')
lock=threading.Lock()
state=None
SERVERLESS=os.getenv('VERCEL') == '1'

def analysis():
    global state
    if state is None:
        path=ROOT/'results/analysis.json'
        if not path.exists(): raise HTTPException(503,'Run python scripts/run_pipeline.py first.')
        state=json.loads(path.read_text(encoding='utf-8'))
    return state

@app.get('/api/health')
def health(): return {'status':'ok','analysis_ready':(ROOT/'results/analysis.json').exists(),'running':lock.locked()}

@app.get('/api/analysis')
def get_analysis(): return analysis()

@app.get('/api/dataset/summary')
def summary(): return analysis()['summary']

@app.get('/api/dataset/columns')
def columns(): return analysis()['quality']['columns']

@app.get('/api/dataset/missing-values')
def missing(): return {c['name']:c['missing'] for c in analysis()['quality']['columns']}

@app.get('/api/dataset/distribution')
def distribution(): return analysis()['distributions']

@app.get('/api/apriori/itemsets')
def itemsets(min_support:float=Query(0,ge=0,le=1),max_itemset_size:int=Query(5,ge=1,le=5),search:str=Query('',max_length=200),top_n:int=Query(100,ge=1,le=100000)):
    matches=[r for r in analysis()['itemsets'] if r['support']>=min_support and r['length']<=max_itemset_size and search.casefold() in ' '.join(r['itemset']).casefold()]
    return {'total':len(matches),'items':matches[:top_n]}

@app.get('/api/apriori/rules')
def rules(f:Annotated[RuleFilter,Query()]): return filter_rules(analysis()['rules'],f)

@app.get('/api/apriori/rules/disease')
def disease_rules(f:Annotated[RuleFilter,Query()]): return filter_rules(analysis()['disease_rules'],f)

@app.get('/api/apriori/top-rules')
def top_rules(f:Annotated[RuleFilter,Query()]): return filter_rules(analysis()['disease_rules' if f.disease_only else 'rules'],f)

@app.get('/api/apriori/metrics')
def metrics():
    return {'summary':analysis()['summary'],'definitions':{'support':'Share of records containing both sides.','confidence':'Share of antecedent records also containing the consequent.','lift':'Confidence divided by consequent prevalence; above 1 indicates positive association.','conviction':'(1 - consequent support) / (1 - confidence). Null with conviction_infinite=true denotes infinity.'}}

@app.post('/api/apriori/filter')
def filtered(f:RuleFilter): return filter_rules(analysis()['disease_rules' if f.disease_only else 'rules'],f)

@app.post('/api/apriori/run')
def run(config:AnalysisConfig):
    global state
    if SERVERLESS:
        raise HTTPException(501,'Running a new analysis is available only in the local application. Vercel deployments show the prepared analysis snapshot.')
    if not lock.acquire(blocking=False): raise HTTPException(409,'Another analysis is running. Try again after completion.')
    try:
        # Build in staging. Readers keep seeing a complete previous snapshot during computation.
        with tempfile.TemporaryDirectory(prefix='dmdw6_') as directory:
            staging=Path(directory)
            result=run_pipeline(config,root=staging)
            from src.reporting import generate_report
            generate_report(result,root=staging)
            for folder in ['results','reports','data/processed','data/intermediate']:
                for source in (staging/folder).rglob('*'):
                    if source.is_file():
                        dest=ROOT/source.relative_to(staging); dest.parent.mkdir(parents=True,exist_ok=True)
                        temporary=dest.with_suffix(dest.suffix+'.new')
                        shutil.copyfile(source,temporary); temporary.replace(dest)
            shutil.copyfile(staging/'REPORT.md',ROOT/'REPORT.md')
            state=result
        return {'message':'Analysis completed successfully','summary':result['summary']}
    except (ValueError,FileNotFoundError) as exc:
        raise HTTPException(400,str(exc)) from exc
    finally: lock.release()

@app.get('/api/export/rules')
def export_rules(f:Annotated[RuleFilter,Query()]):
    rows=filter_rules(analysis()['disease_rules' if f.disease_only else 'rules'],f)['items']
    stream=io.StringIO(newline='')
    fields=list(rows[0]) if rows else ['antecedents','consequents','support','confidence','lift','leverage','conviction']
    writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
    for row in rows: writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
    return Response(stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=filtered_rules.csv'})

@app.get('/api/export/{kind}')
def export(kind:str):
    paths={'itemsets':'results/frequent_itemsets.csv','cleaned':'data/processed/cleaned_dataset.csv',
           'analysis':'results/analysis.json','report':'REPORT.md','pdf':'reports/DMDW6_Report.pdf',
           'all-rules':'results/association_rules.csv','disease-rules':'results/disease_rules.csv'}
    if kind not in paths: raise HTTPException(404,'Unknown export type.')
    path=ROOT/paths[kind]
    if not path.is_file(): raise HTTPException(404,'Export not generated yet.')
    return FileResponse(path,filename=path.name)

if (ROOT/'frontend/dist').exists():
    app.mount('/',StaticFiles(directory=ROOT/'frontend/dist',html=True),name='dashboard')
