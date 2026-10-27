"""Local single-user FastAPI service with isolated dataset workspaces."""
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from src.pipeline import AnalysisConfig, RuleFilter, filter_rules, run_pipeline
from src.datasets import DATASETS, DEFAULT_DATASET, dataset_spec, dataset_root
from src.symptom_pipeline import run_symptom_pipeline

app = FastAPI(title='DMDW6 Apriori API', version='1.1.0')
from backend.app.upload_demo import router as upload_demo_router
app.include_router(upload_demo_router)
# One writer also protects the shared report-rendering library. Readers keep their complete snapshot.
lock = threading.Lock()
state = None  # Backward-compatible default-dataset cache.
dataset_states = {}
SERVERLESS = os.getenv('VERCEL') == '1'


def spec_for(dataset_id):
    try:
        return dataset_spec(dataset_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


def workspace(dataset_id):
    spec_for(dataset_id)
    return dataset_root(ROOT, dataset_id)


def analysis(dataset_id=DEFAULT_DATASET):
    global state
    spec = spec_for(dataset_id)
    key = (str(ROOT), dataset_id)
    snapshot = state if dataset_id == DEFAULT_DATASET else dataset_states.get(key)
    if snapshot is None:
        path = workspace(dataset_id) / 'results/analysis.json'
        if not path.exists():
            raise HTTPException(503, f'No prepared analysis for {dataset_id}. Run scripts/run_pipeline.py --dataset {dataset_id}.')
        snapshot = json.loads(path.read_text(encoding='utf-8'))
        if dataset_id == DEFAULT_DATASET:
            state = snapshot
        else:
            dataset_states[key] = snapshot
    return {**snapshot, 'dataset': spec}


@app.get('/api/datasets')
def datasets():
    return {
        'default': DEFAULT_DATASET, 'can_run': not SERVERLESS,
        'datasets': [{**spec, 'ready': (workspace(key) / 'results/analysis.json').exists()}
                     for key, spec in DATASETS.items()],
    }


@app.get('/api/health')
def health():
    return {'status': 'ok', 'analysis_ready': (ROOT / 'results/analysis.json').exists(),
            'running': lock.locked()}


@app.get('/api/analysis')
@app.get('/api/datasets/{dataset_id}/analysis')
def get_analysis(dataset_id: str = DEFAULT_DATASET):
    return analysis(dataset_id)


@app.get('/api/dataset/summary')
@app.get('/api/datasets/{dataset_id}/dataset/summary')
def summary(dataset_id: str = DEFAULT_DATASET):
    return analysis(dataset_id)['summary']


@app.get('/api/dataset/columns')
@app.get('/api/datasets/{dataset_id}/dataset/columns')
def columns(dataset_id: str = DEFAULT_DATASET):
    return analysis(dataset_id)['quality']['columns']


@app.get('/api/dataset/missing-values')
@app.get('/api/datasets/{dataset_id}/dataset/missing-values')
def missing(dataset_id: str = DEFAULT_DATASET):
    return {column['name']: column['missing'] for column in analysis(dataset_id)['quality']['columns']}


@app.get('/api/dataset/distribution')
@app.get('/api/datasets/{dataset_id}/dataset/distribution')
def distribution(dataset_id: str = DEFAULT_DATASET):
    return analysis(dataset_id)['distributions']


@app.get('/api/apriori/itemsets')
@app.get('/api/datasets/{dataset_id}/apriori/itemsets')
def itemsets(min_support: float = Query(0, ge=0, le=1), max_itemset_size: int = Query(5, ge=1, le=5),
             search: str = Query('', max_length=200), top_n: int = Query(100, ge=1, le=100000),
             dataset_id: str = DEFAULT_DATASET):
    matches = [row for row in analysis(dataset_id)['itemsets']
               if row['support'] >= min_support and row['length'] <= max_itemset_size
               and search.casefold() in ' '.join(row['itemset']).casefold()]
    return {'total': len(matches), 'items': matches[:top_n]}


@app.get('/api/datasets/{dataset_id}/apriori/rules')
def rules(f: Annotated[RuleFilter, Query()], dataset_id: str = DEFAULT_DATASET):
    return filter_rules(analysis(dataset_id)['rules'], f)


@app.get('/api/datasets/{dataset_id}/apriori/rules/disease')
def disease_rules(f: Annotated[RuleFilter, Query()], dataset_id: str = DEFAULT_DATASET):
    return filter_rules(analysis(dataset_id)['disease_rules'], f)


@app.get('/api/datasets/{dataset_id}/apriori/top-rules')
def top_rules(f: Annotated[RuleFilter, Query()], dataset_id: str = DEFAULT_DATASET):
    return filter_rules(analysis(dataset_id)['disease_rules' if f.disease_only else 'rules'], f)


@app.get('/api/apriori/metrics')
@app.get('/api/datasets/{dataset_id}/apriori/metrics')
def metrics(dataset_id: str = DEFAULT_DATASET):
    return {'summary': analysis(dataset_id)['summary'], 'definitions': {
        'support': 'Share of records containing both sides.',
        'confidence': 'Share of antecedent records also containing the consequent.',
        'lift': 'Confidence divided by consequent prevalence; above 1 indicates positive association.',
        'conviction': '(1 - consequent support) / (1 - confidence). Null with conviction_infinite=true denotes infinity.',
    }}


@app.post('/api/apriori/filter')
@app.post('/api/datasets/{dataset_id}/apriori/filter')
def filtered(f: RuleFilter, dataset_id: str = DEFAULT_DATASET):
    return filter_rules(analysis(dataset_id)['disease_rules' if f.disease_only else 'rules'], f)


@app.post('/api/apriori/run')
@app.post('/api/datasets/{dataset_id}/apriori/run')
def run(config: AnalysisConfig, dataset_id: str = DEFAULT_DATASET):
    global state
    spec = spec_for(dataset_id)
    config = AnalysisConfig(**{**spec['default_config'], **config.model_dump(exclude_unset=True)})
    if SERVERLESS:
        raise HTTPException(501, 'Running a new analysis is available only in the local application. Vercel deployments show the prepared analysis snapshots.')
    if config.max_itemset_size > spec['max_itemset_size']:
        raise HTTPException(422, f"This dataset supports combinations up to {spec['max_itemset_size']} items.")
    if not lock.acquire(blocking=False):
        raise HTTPException(409, 'Another analysis is running. Try again after completion.')
    try:
        destination = workspace(dataset_id)
        with tempfile.TemporaryDirectory(prefix=f'dmdw6_{dataset_id}_') as directory:
            staging = Path(directory)
            if dataset_id == DEFAULT_DATASET:
                result = run_pipeline(config, root=staging)
            else:
                result = run_symptom_pipeline(config, root=staging, raw_path=destination / 'data/raw/dataset.csv')
            from src.reporting import generate_report
            generate_report(result, root=staging)
            for folder in ['results', 'reports', 'data/processed', 'data/intermediate']:
                for source in (staging / folder).rglob('*'):
                    if source.is_file():
                        dest = destination / source.relative_to(staging)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        temporary = dest.with_suffix(dest.suffix + '.new')
                        shutil.copyfile(source, temporary)
                        temporary.replace(dest)
            temporary_report = destination / 'REPORT.md.new'
            shutil.copyfile(staging / 'REPORT.md', temporary_report)
            temporary_report.replace(destination / 'REPORT.md')
            if dataset_id == DEFAULT_DATASET:
                state = result
            else:
                dataset_states[(str(ROOT), dataset_id)] = result
        return {'message': 'Analysis completed successfully', 'dataset_id': dataset_id, 'summary': result['summary']}
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        lock.release()


@app.get('/api/datasets/{dataset_id}/export/rules')
def export_rules(f: Annotated[RuleFilter, Query()], dataset_id: str = DEFAULT_DATASET):
    rows = filter_rules(analysis(dataset_id)['disease_rules' if f.disease_only else 'rules'], f)['items']
    stream = io.StringIO(newline='')
    fields = list(rows[0]) if rows else ['antecedents', 'consequents', 'support', 'confidence', 'lift', 'leverage', 'conviction']
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value) if isinstance(value, list) else value for key, value in row.items()})
    filename = 'filtered_rules.csv' if dataset_id == DEFAULT_DATASET else f'{dataset_id}_filtered_rules.csv'
    return Response(stream.getvalue(), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename={filename}'})


@app.get('/api/datasets/{dataset_id}/export/{kind}')
def export(kind: str, dataset_id: str = DEFAULT_DATASET):
    paths = {
        'itemsets': 'results/frequent_itemsets.csv', 'cleaned': 'data/processed/cleaned_dataset.csv',
        'analysis': 'results/analysis.json', 'report': 'REPORT.md', 'pdf': 'reports/DMDW6_Report.pdf',
        'all-rules': 'results/association_rules.csv', 'disease-rules': 'results/disease_rules.csv',
    }
    destination = workspace(dataset_id)
    if kind not in paths:
        raise HTTPException(404, 'Unknown export type.')
    path = destination / paths[kind]
    if not path.is_file():
        raise HTTPException(404, 'Export not generated yet.')
    filename = path.name if dataset_id == DEFAULT_DATASET else f'{dataset_id}_{path.name}'
    return FileResponse(path, filename=filename)


# Keep the original query-model endpoints unchanged. A path parameter selects the new source.
@app.get('/api/apriori/rules')
def default_rules(f: Annotated[RuleFilter, Query()]):
    return rules(f)


@app.get('/api/apriori/rules/disease')
def default_disease_rules(f: Annotated[RuleFilter, Query()]):
    return disease_rules(f)


@app.get('/api/apriori/top-rules')
def default_top_rules(f: Annotated[RuleFilter, Query()]):
    return top_rules(f)


@app.get('/api/export/rules')
def default_export_rules(f: Annotated[RuleFilter, Query()]):
    return export_rules(f)


app.get('/api/export/{kind}')(export)


if (ROOT / 'frontend/dist').exists():
    app.mount('/', StaticFiles(directory=ROOT / 'frontend/dist', html=True), name='dashboard')
