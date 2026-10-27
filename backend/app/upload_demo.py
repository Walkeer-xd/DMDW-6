"""Request-scoped upload analysis: streamed evidence, no persistent dataset changes."""
import csv
import io
import json
from pathlib import Path
from queue import Queue
import tempfile
import threading

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse

from src.datasets import dataset_spec
from src.pipeline import AnalysisConfig, normalize_name, run_pipeline
from src.symptom_pipeline import run_symptom_pipeline

router = APIRouter()
MAX_BYTES = 1_000_000
demo_lock = threading.Lock()
SAMPLES = Path(__file__).resolve().parents[2] / 'data/demo'


@router.get('/api/demo/sample/{kind}')
def sample(kind: str):
    if kind not in {'profiles', 'symptoms'}:
        raise HTTPException(404, 'Unknown sample format.')
    return Response((SAMPLES / f'presentation_{kind}.csv').read_bytes(), media_type='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=presentation_{kind}.csv'})


@router.post('/api/demo/analyze')
async def analyze_upload(request: Request,
                         min_support: float = Query(.05, ge=.05, le=1),
                         min_confidence: float = Query(.3, ge=0, le=1),
                         min_lift: float = Query(1.2, ge=0, le=1000),
                         remove_duplicates: bool = True):
    # Read incrementally so a large body cannot bypass the advertised upload limit.
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BYTES:
            raise HTTPException(413, 'Upload a CSV smaller than 1 MB.')
    try:
        text = body.decode('utf-8-sig')
        if '\x00' in text:
            raise ValueError('Binary files are not supported.')
        rows = list(csv.reader(io.StringIO(text), strict=True))
        if len(rows) < 2 or len(rows) > 1001:
            raise ValueError('Use a CSV containing 1–1,000 data rows and a header.')
        headers = rows[0]
        if len(headers) > 20 or len(headers) != len(set(headers)):
            raise ValueError('Use at most 20 distinct column names.')
        if any(len(row) != len(headers) for row in rows[1:]):
            raise ValueError('Every CSV row must have the same number of fields as the header.')
        if any(len(cell) > 120 for row in rows for cell in row):
            raise ValueError('Keep column names and cell values within 120 characters.')
        symptom_headers = ['Disease', *[f'Symptom_{i}' for i in range(1, 18)]]
        kind = 'symptoms' if headers == symptom_headers else 'profiles'
        if kind == 'profiles':
            required = {'Disease', 'Age', 'Gender', 'Blood_Pressure', 'Cholesterol_Level',
                        'Fever', 'Cough', 'Fatigue', 'Difficulty_Breathing'}
            normalized = [normalize_name(column) for column in headers]
            if not required.issubset(normalized) or len(set(normalized)) != len(headers):
                raise ValueError('Use the patient-profile or symptom-list CSV format. Download a sample below for the required columns.')
        # Bound the item vocabulary before Apriori allocates its candidate matrix.
        if kind == 'symptoms':
            vocabulary = {cell.strip() for row in rows[1:] for cell in row if cell.strip()}
        else:
            disease_index = normalized.index('Disease')
            vocabulary = {row[disease_index].strip() for row in rows[1:]}
        if len(vocabulary) > 150:
            raise ValueError('Use at most 150 distinct disease and symptom labels for the live demo.')
    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc

    if not demo_lock.acquire(blocking=False):
        raise HTTPException(409, 'Another upload demo is running. Try again after it finishes.')
    events = Queue()

    def emit(step, message, details=None):
        events.put({'type': 'step', 'step': step, 'message': message, **(details or {})})

    def worker():
        try:
            with tempfile.TemporaryDirectory(prefix='association_demo_') as directory:
                root = Path(directory)
                raw = root / 'upload.csv'
                raw.write_bytes(body)
                config = AnalysisConfig(min_support=min_support, min_confidence=min_confidence,
                                        min_lift=min_lift, max_itemset_size=3, max_rules=5000,
                                        remove_duplicates=remove_duplicates)
                emit('validate', f'Validated {kind} CSV. Running with support ≥ {min_support:.0%}, confidence ≥ {min_confidence:.0%}, lift ≥ {min_lift:g}; combinations up to 3 items.')
                pipeline = run_symptom_pipeline if kind == 'symptoms' else run_pipeline
                result = pipeline(config, root=root, raw_path=raw, progress=emit)
                spec = {**dataset_spec(kind), 'name': 'Temporary upload',
                        'title': 'Uploaded presentation dataset', 'source': '',
                        'source_label': 'User-provided CSV; provenance not verified'}
                result['dataset'] = spec
                result['summary']['source'] = ''
                result['quality']['source'] = 'Temporary user upload'
                result['quality']['filename'] = 'upload.csv'
                result['cleaning']['decisions'] = [
                    'Uploaded CSV is processed in a temporary directory, deleted before results are sent.',
                    *[decision for decision in result['cleaning']['decisions']
                      if not any(word in decision.lower() for word in ['downloaded', 'byte-for-byte', 'kaggle', 'workspace'])],
                ]
                artifacts = {key: (root / path).read_text(encoding='utf-8') for key, path in {
                    'cleaned': 'data/processed/cleaned_dataset.csv',
                    'rules': 'results/association_rules.csv',
                    'disease-rules': 'results/disease_rules.csv',
                    'itemsets': 'results/frequent_itemsets.csv',
                    'transactions': 'data/intermediate/transactions.csv',
                }.items()}
            emit('results', f"Calculated {len(result['rules']):,} rules, including {len(result['disease_rules']):,} disease associations. Temporary server files deleted.")
            events.put({'type': 'complete', 'analysis': result, 'artifacts': artifacts})
        except Exception as exc:
            events.put({'type': 'error', 'message': str(exc) if isinstance(exc, ValueError)
                        else 'Analysis failed. Check your CSV format and try again.'})
        finally:
            demo_lock.release()
            events.put(None)

    def stream():
        while True:
            event = events.get()
            if event is None:
                break
            yield json.dumps(event, allow_nan=False) + '\n'

    threading.Thread(target=worker, daemon=True).start()
    return StreamingResponse(stream(), media_type='application/x-ndjson', headers={
        'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no',
    })
