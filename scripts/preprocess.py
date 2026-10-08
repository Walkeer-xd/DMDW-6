import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.pipeline import ROOT, load_raw, audit, clean, encode, save_json
raw=load_raw(); cleaned,log=clean(raw); transactions,matrix,mapping=encode(cleaned,raw)
cleaned.to_csv(ROOT/'data/processed/cleaned_dataset.csv',index=False)
save_json(ROOT/'results/data_quality.json',audit(raw))
save_json(ROOT/'results/preprocessing_metadata.json',{'cleaning_log':log,'feature_mapping':mapping})
save_json(ROOT/'data/intermediate/transactions.json',transactions)
matrix.to_csv(ROOT/'data/intermediate/encoded_transactions.csv',index=False)
print(f'Prepared {len(cleaned)} records and {len(matrix.columns)} items.')
