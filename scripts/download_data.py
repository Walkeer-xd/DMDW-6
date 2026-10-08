"""Download the exact source; never overwrite an existing raw file."""
from pathlib import Path
import hashlib
import io
import json
import urllib.request
import zipfile
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data/raw/Disease_symptom_and_patient_profile_dataset.csv'
if DEST.exists():
    print(f'Preserved existing dataset: {DEST}')
else:
    url='https://www.kaggle.com/api/v1/datasets/download/uom190346a/disease-symptoms-and-patient-profile-dataset?datasetVersionNumber=2'
    data=urllib.request.urlopen(url,timeout=90).read()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        matches=[n for n in archive.namelist() if Path(n).name==DEST.name]
        if len(matches)!=1: raise ValueError('Expected source CSV not found in download.')
        DEST.parent.mkdir(parents=True,exist_ok=True)
        content=archive.read(matches[0])
        expected='79cd5314cfdefec9b86ee0efd63d3df64a619a2e2511c5908abde008edf1bfa8'
        if hashlib.sha256(content).hexdigest()!=expected:
            raise ValueError('Source checksum differs from the verified project dataset. Review the source version before continuing.')
        DEST.write_bytes(content)
print('SHA256:',hashlib.sha256(DEST.read_bytes()).hexdigest())
