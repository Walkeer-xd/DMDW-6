"""Audit, clean and mine the exact referenced dataset; no generated patient data."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import math
import re

import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/Disease_symptom_and_patient_profile_dataset.csv'
SOURCE = 'https://www.kaggle.com/datasets/uom190346a/disease-symptoms-and-patient-profile-dataset'
SYMPTOMS = ['Fever', 'Cough', 'Fatigue', 'Difficulty_Breathing']
MISSING = {'', '?', 'na', 'n/a', 'null', 'none', 'nan', 'unknown', 'unavailable'}
NOTICE = 'The discovered rules represent statistical associations in the dataset and should not be interpreted as medical causation, diagnosis, or clinical recommendations.'
DECISIONS = [
    'Preserve the source CSV byte-for-byte; audit before transformation.',
    'Remove exact duplicate rows by default for a unique-profile analysis. Without patient IDs their identity cannot be established; --keep-duplicates provides a sensitivity analysis.',
    'Trim whitespace and normalize field names. Standardize categorical case without guessing disease synonyms or expanding truncated labels.',
    'Unknown, missing and invalid observations remain Unknown. They are omitted from transactions, never converted into symptom absence.',
    'Keep explicit Yes and No symptom items: recorded absence is different from missingness.',
    'Bin integer ages into 0-17, 18-30, 31-45, 46-60 and 61+. These are descriptive groups, not clinical risk categories.',
    'Exclude Outcome_Variable from all mining because its semantics are insufficiently documented and it could mix downstream outcomes into profile associations.',
    'Keep Disease in transactions; primary disease rules have exactly one Disease consequent and no Disease antecedent.',
    'Retain truncated disease names and possible aliases separately; flag them for source review instead of inventing corrections.'
]

class AnalysisConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    min_support: float = Field(.02, ge=.005, le=1)
    min_confidence: float = Field(.30, ge=0, le=1)
    min_lift: float = Field(1.20, ge=0, le=1000)
    max_itemset_size: int = Field(4, ge=2, le=5)
    max_rules: int = Field(20000, ge=1, le=100000)
    remove_duplicates: bool = True

class RuleFilter(BaseModel):
    model_config = ConfigDict(extra='forbid')
    min_support: float = Field(0, ge=0, le=1)
    min_confidence: float = Field(0, ge=0, le=1)
    min_lift: float = Field(0, ge=0, le=1000)
    max_antecedent_length: int = Field(5, ge=1, le=5)
    disease: str = Field('', max_length=150)
    symptom: str = Field('', max_length=100)
    search: str = Field('', max_length=200)
    item: str = Field('', max_length=200)
    top_n: int = Field(100, ge=1, le=100000)
    sort_by: str = Field('lift', pattern='^(lift|confidence|support|leverage|conviction|antecedent_support|consequent_support|item_count)$')
    descending: bool = True
    disease_only: bool = False

def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')

def load_raw(path=RAW):
    if not Path(path).is_file():
        raise FileNotFoundError(f'Place the original CSV at {path}, or run python scripts/download_data.py.')
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if frame.empty:
        raise ValueError('Dataset contains no records.')
    return frame

def normalize_name(name):
    return re.sub(r'[^A-Za-z0-9]+', '_', name.strip()).strip('_')

def target_column(frame):
    candidates = [c for c in frame.columns if normalize_name(c).lower() in {'disease', 'diagnosis', 'class'}]
    if len(candidates) != 1:
        raise ValueError('Expected one clearly identifiable Disease/Diagnosis/Class column.')
    return candidates[0]

def audit(frame):
    columns = []
    for c in frame:
        s = frame[c].astype(str)
        missing = s.str.strip().str.lower().isin(MISSING)
        numeric = pd.to_numeric(s[~missing], errors='coerce')
        is_numeric = bool(len(numeric) and numeric.notna().all())
        variants = {}
        for value in sorted(s.unique()):
            variants.setdefault(value.strip().casefold(), []).append(value)
        columns.append({
            'name': c, 'normalized_name': normalize_name(c), 'dtype': 'numeric' if is_numeric else 'categorical',
            'storage_dtype': str(frame[c].dtype), 'missing': int(missing.sum()),
            'unique_count': int(s.nunique()), 'unique_values': sorted(s.unique().tolist()),
            'binary': len(s[~missing].unique()) == 2,
            'whitespace_count': int((s != s.str.strip()).sum()),
            'case_variants': [v for v in variants.values() if len(v) > 1],
            'missing_markers': s[missing].value_counts().to_dict(),
            'numeric_summary': {k: float(v) for k, v in numeric.describe().to_dict().items()} if is_numeric else None,
            'treatment': 'Descriptive age bins' if c.strip().lower() == 'age' else ('Excluded from mining' if normalize_name(c) == 'Outcome_Variable' else 'Named categorical items; unknowns omitted'),
        })
    t = target_column(frame)
    suspicious = []
    for c in frame:
        for value in sorted(frame[c].astype(str).unique()):
            if '...' in value:
                suspicious.append({'column': c, 'value': value, 'issue': 'Truncated label; retained without expansion'})
    if 'Urinary Tract Infection' in set(frame[t]) and 'Urinary Tract Infection (UTI)' in set(frame[t]):
        suspicious.append({'column': t, 'value': 'Urinary Tract Infection / Urinary Tract Infection (UTI)', 'issue': 'Possible alias; retained separately without authoritative mapping'})
    return {'rows': len(frame), 'column_count': len(frame.columns), 'columns': columns,
            'duplicate_rows': int(frame.duplicated().sum()), 'missing_values': sum(c['missing'] for c in columns),
            'numerical_columns': [c['name'] for c in columns if c['dtype'] == 'numeric'],
            'categorical_columns': [c['name'] for c in columns if c['dtype'] == 'categorical'],
            'binary_columns': [c['name'] for c in columns if c['binary']],
            'target_column': t, 'disease_distribution': frame[t].value_counts().to_dict(),
            'suspicious_values': suspicious, 'filename': RAW.name, 'source': SOURCE}

def clean(frame, remove_duplicates=True):
    before = audit(frame)
    t = target_column(frame)
    result = frame.copy()
    removed = int(result.duplicated().sum()) if remove_duplicates else 0
    if remove_duplicates:
        result = result.drop_duplicates().copy()
    result.columns = [normalize_name(c) for c in result.columns]
    result = result.rename(columns={normalize_name(t): 'Disease'})
    if len(set(result.columns)) != len(result.columns):
        raise ValueError('Column normalization produced ambiguous duplicate names.')
    required = {'Disease', 'Age', 'Gender', 'Blood_Pressure', 'Cholesterol_Level', *SYMPTOMS}
    if not required.issubset(result.columns):
        raise ValueError(f'Missing required columns: {sorted(required-set(result.columns))}')
    invalid = []
    for c in result:
        result[c] = result[c].astype(str).str.strip()
        result.loc[result[c].str.casefold().isin(MISSING), c] = 'Unknown'
        if c in SYMPTOMS:
            mapping = {'yes':'Yes','no':'No','true':'Yes','false':'No','1':'Yes','0':'No','unknown':'Unknown'}
        elif c in {'Blood_Pressure', 'Cholesterol_Level'}:
            mapping = {v.lower():v for v in ['High','Normal','Low','Unknown']}
        elif c == 'Gender':
            mapping = {v.lower():v for v in ['Male','Female','Other','Unknown']}
        elif c == 'Outcome_Variable':
            mapping = {v.lower():v for v in ['Positive','Negative','Unknown']}
        else:
            mapping = None
        if mapping:
            mapped = result[c].str.lower().map(mapping)
            for idx in result.index[mapped.isna()]:
                invalid.append({'row': int(idx)+2, 'column': c, 'value': result.at[idx,c], 'action': 'Unknown'})
            result[c] = mapped.fillna('Unknown')
    # Preserve the first source spelling while collapsing only case/whitespace variants.
    spellings = {}
    result['Disease'] = result['Disease'].map(lambda v: spellings.setdefault(v.casefold(), v))
    age = pd.to_numeric(result['Age'], errors='coerce')
    valid = age.between(0,120) & (age % 1 == 0)
    for idx in result.index[~valid & result['Age'].ne('Unknown')]:
        invalid.append({'row':int(idx)+2, 'column':'Age', 'value':result.at[idx,'Age'], 'action':'Unknown'})
    result['Age'] = age.where(valid).astype('Int64')
    result['Age_Group'] = pd.cut(result['Age'].astype(float), [-1,17,30,45,60,120], labels=['0-17','18-30','31-45','46-60','61+']).astype('string').fillna('Unknown')
    result = result.reset_index(drop=True)
    log = {'original_rows':len(frame), 'cleaned_rows':len(result), 'duplicate_rows_removed':removed,
           'missing_values_before': before['missing_values'],
           'missing_values_after': int(result.drop(columns='Age_Group').isna().sum().sum() + result.drop(columns='Age_Group').eq('Unknown').sum().sum()),
           'invalid_values_fixed':len(invalid), 'invalid_value_details':invalid,
           'columns_removed':[], 'columns_excluded_from_mining':['Outcome_Variable','Age'],
           'columns_transformed':dict(zip(frame.columns,[normalize_name(c) for c in frame.columns])),
           'decisions':DECISIONS, 'duplicate_policy':'remove exact duplicates' if remove_duplicates else 'retain all rows'}
    return result, log

def encode(frame, raw=None):
    features = SYMPTOMS + ['Gender','Blood_Pressure','Cholesterol_Level','Age_Group','Disease']
    transactions = []
    for row in frame.to_dict('records'):
        items = sorted(f'{c}={row[c]}' for c in features if pd.notna(row[c]) and row[c] != 'Unknown')
        if not items:
            raise ValueError('An entirely unknown record cannot form a transaction.')
        transactions.append(items)
    encoder = TransactionEncoder()
    matrix = pd.DataFrame(encoder.fit(transactions).transform(transactions), columns=encoder.columns_)
    metadata = []
    if raw is not None:
        for original in raw:
            transformed = normalize_name(original)
            if original == target_column(raw):
                transformed = 'Disease'
            for value in sorted(raw[original].unique()):
                # Map through the same cleaning function, never a separate encoding convention.
                row, _ = clean(raw.loc[raw[original].eq(value)].head(1), False)
                if transformed == 'Age':
                    destination, mapped = 'Age_Group', row.iloc[0]['Age_Group']
                    reason = 'Inclusive bins: 0-17, 18-30, 31-45, 46-60, 61-120; unknown omitted'
                else:
                    destination, mapped = transformed, row.iloc[0][transformed]
                    reason = 'Readable categorical item; explicit Yes and No retained'
                included = destination in features and pd.notna(mapped) and mapped != 'Unknown'
                metadata.append({'original_column':original,'transformed_column':destination,'original_value':value,
                                 'new_item_label':f'{destination}={mapped}' if included else None,
                                 'reason':reason if included else 'Excluded outcome or unknown value'})
    return transactions, matrix, metadata

def is_disease_rule(rule):
    return len(rule['consequents']) == 1 and rule['consequents'][0].startswith('Disease=') and not any(x.startswith('Disease=') for x in rule['antecedents'])

def rank_rules(rules):
    return sorted(rules, key=lambda r: (-r['lift'], -r['confidence'], -r['support'], r['antecedents'], r['consequents']))

def mine(matrix, config, progress=None):
    frequent = apriori(matrix, min_support=config.min_support, use_colnames=True, max_len=config.max_itemset_size)
    itemsets = sorted([{'itemset': sorted(r.itemsets), 'support':float(r.support),
                        'item_count':int(round(r.support*len(matrix))), 'length':len(r.itemsets)}
                       for r in frequent.itertuples()], key=lambda r:(-r['support'],r['length'],r['itemset']))
    if progress:
        progress('itemsets', f'Found {len(itemsets):,} frequent itemsets. Generating rules and calculating support, confidence and lift.', {'preview': itemsets[:5]})
    rules = []
    if len(frequent) and frequent.itemsets.map(len).max() >= 2:
        table = association_rules(frequent, num_itemsets=len(matrix), metric='confidence', min_threshold=config.min_confidence)
        for r in table.to_dict('records'):
            if r['lift'] + 1e-12 < config.min_lift:
                continue
            out = {'antecedents':sorted(r.pop('antecedents')), 'consequents':sorted(r.pop('consequents'))}
            for k,v in r.items():
                out[k.replace(' ','_')] = float(v) if np.isfinite(v) else None
            out['conviction_infinite'] = bool(np.isposinf(r.get('conviction', 0)))
            out['item_count'] = int(round(out['support']*len(matrix)))
            out['antecedent_count'] = int(round(out['antecedent_support']*len(matrix)))
            rules.append(out)
    rules = rank_rules(rules)
    disease = [r for r in rules if is_disease_rule(r)]
    counts = {'association_rules_before_cap':len(rules), 'disease_rules_before_cap':len(disease)}
    # Independent caps prevent general rules from crowding all disease rules out.
    return itemsets, rules[:config.max_rules], disease[:config.max_rules], counts

def filter_rules(rules, f):
    matches = [r for r in rules if r['support']+1e-12 >= f.min_support and r['confidence']+1e-12 >= f.min_confidence
               and r['lift']+1e-12 >= f.min_lift and len(r['antecedents']) <= f.max_antecedent_length
               and (not f.disease_only or is_disease_rule(r))
               and (not f.disease or f'Disease={f.disease}' in r['consequents'])
               and (not f.symptom or any(x.split('=')[0] == f.symptom for x in r['antecedents']))
               and (not f.item or f.item in r['antecedents'] or f.item in r['consequents'])
               and f.search.casefold() in ' '.join(r['antecedents']+r['consequents']).casefold()]
    def score(r):
        return math.inf if f.sort_by == 'conviction' and r['conviction_infinite'] else (r.get(f.sort_by) or 0)
    matches.sort(key=score, reverse=f.descending)
    return {'total':len(matches),'items':matches[:f.top_n]}

def write_csv(path, records, fields):
    data = [{k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in r.items()} for r in records]
    pd.DataFrame(data, columns=list(data[0]) if data else fields).to_csv(path,index=False)

def run_pipeline(config=None, root=ROOT, raw_path=RAW, progress=None):
    config = config or AnalysisConfig()
    for p in ['results','data/processed','data/intermediate','reports']:
        (root/p).mkdir(parents=True,exist_ok=True)
    raw = load_raw(raw_path)
    if progress:
        progress('read', f'Read {len(raw):,} rows and {len(raw.columns)} columns.', {'preview': raw.head(5).to_dict('records')})
    quality = audit(raw)
    if progress:
        progress('audit', f"Found {quality['duplicate_rows']} exact duplicate rows and {quality['missing_values']} empty or unknown cells.")
    cleaned, log = clean(raw, config.remove_duplicates)
    if progress:
        progress('clean', f"Retained {len(cleaned)} rows; removed {log['duplicate_rows_removed']} duplicates and handled {log['invalid_values_fixed']} invalid values.", {'preview': json.loads(cleaned.head(5).to_json(orient='records'))})
    transactions, matrix, mapping = encode(cleaned,raw)
    if progress:
        progress('encode', f'Encoded {len(transactions)} transactions across {len(matrix.columns)} distinct items. Starting Apriori.', {'transactions': transactions[:5], 'matrix': matrix.iloc[:5, :12].astype(int).to_dict('records')})
    itemsets, rules, disease, counts = mine(matrix,config,progress)
    distributions = {c:cleaned[c].fillna('Unknown').astype(str).value_counts().to_dict() for c in cleaned if c != 'Age'}
    summary = {'title':'Association Rule Mining using Apriori on Disease Symptoms and Patient Profiles',
               'raw_records':len(raw),'records':len(cleaned),'attributes':len(raw.columns),
               'cleaned_attributes':len(cleaned.columns),'mining_features':9,'disease_classes':int(cleaned['Disease'].nunique()),
               'missing_values':quality['missing_values'],'duplicate_records':quality['duplicate_rows'],
               'frequent_itemsets':len(itemsets),'association_rules':len(rules),'disease_rules':len(disease),
               'strong_rules':sum(r['lift']>1 and r['confidence']>=.7 for r in rules),
               'strong_rule_definition':'confidence >= 0.70 and lift > 1 among exported rules',
               'distinct_items':len(matrix.columns),'minimum_count':math.ceil(config.min_support*len(cleaned)-1e-12),
               'generated_at':datetime.now(timezone.utc).isoformat(),'raw_sha256':sha256(Path(raw_path).read_bytes()).hexdigest(),
               'source':SOURCE,'notice':NOTICE,**counts}
    result = {'summary':summary,'config':config.model_dump(),'quality':quality,'cleaning':log,
              'distributions':distributions,'itemsets':itemsets,'rules':rules,'disease_rules':disease,
              'symptoms':SYMPTOMS,'mapping':mapping}
    cleaned.to_csv(root/'data/processed/cleaned_dataset.csv', index=False)
    save_json(root/'data/intermediate/transactions.json',transactions)
    pd.DataFrame({'transaction_id':range(1,len(transactions)+1),'items':[json.dumps(t) for t in transactions]}).to_csv(root/'data/intermediate/transactions.csv',index=False)
    matrix.to_csv(root/'data/intermediate/encoded_transactions.csv',index=False)
    for name, data, fields in [('frequent_itemsets',itemsets,['itemset','support','item_count','length']),
                                ('association_rules',rules,['antecedents','consequents','support','confidence','lift','leverage','conviction']),
                                ('disease_rules',disease,['antecedents','consequents','support','confidence','lift','leverage','conviction'])]:
        write_csv(root/f'results/{name}.csv',data,fields)
    for name, obj in [('summary',summary),('data_quality',quality),('preprocessing_metadata',{'cleaning_log':log,'feature_mapping':mapping}),('analysis_config',config.model_dump()),('analysis',result)]:
        save_json(root/f'results/{name}.json',obj)
    return result
