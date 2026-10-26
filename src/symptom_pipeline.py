"""Adapt the Kaggle symptom-list benchmark without fabricating absent symptoms."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import math
import json

import pandas as pd
from mlxtend.preprocessing import TransactionEncoder

from src.datasets import dataset_spec
from src.pipeline import NOTICE, audit, load_raw, mine, normalize_name, save_json, write_csv

DECISIONS = [
    'Preserve the downloaded dataset.csv byte-for-byte in this dataset workspace.',
    'Remove exact duplicate source rows by default; repeated benchmark profiles are not independent clinical evidence.',
    'Trim disease labels and symptom names. Preserve disease spellings rather than inventing alias corrections.',
    'Convert each nonempty symptom slot to a readable symptom=Yes item; each symptom appears at most once per transaction.',
    'An empty symptom slot contributes no item. An unlisted symptom is unobserved, not a recorded No.',
    'Do not create age, gender, blood pressure, cholesterol, outcome, or negative symptom observations: the source does not supply them.',
    'Keep one Disease item in each transaction; disease rules have one Disease consequent and none in their antecedents.',
    'Keep this source and its analysis separate from the original patient-profile dataset and from overlapping Kaggle copies.',
]


def prepare_symptoms(raw, remove_duplicates=True):
    slots = [f'Symptom_{i}' for i in range(1, 18)]
    if list(raw.columns) != ['Disease', *slots]:
        raise ValueError('Expected Disease and Symptom_1 through Symptom_17 in the symptom-list dataset.')
    quality = audit(raw)
    quality.update(filename='dataset.csv', source=dataset_spec('symptoms')['source'])
    for column in quality['columns']:
        column['treatment'] = ('Trim disease label; keep source spelling' if column['name'] == 'Disease'
                               else 'Trim symptom name; an empty slot contributes no item, never No')
    frame = raw.drop_duplicates().copy() if remove_duplicates else raw.copy()
    frame = frame.reset_index(drop=True)
    for column in frame:
        frame[column] = frame[column].astype(str).str.strip()
    if frame['Disease'].str.casefold().isin({'', 'unknown', 'nan', 'null', '?'}).any():
        raise ValueError('Every symptom profile must have a recorded disease label.')

    spellings = {}
    frame['Disease'] = frame['Disease'].map(lambda value: spellings.setdefault(value.casefold(), value))
    labels = {}
    transactions, symptom_counts, lengths = [], Counter(), Counter()
    for row in frame.to_dict('records'):
        symptoms = set()
        for slot in slots:
            value = row[slot]
            if not value:
                continue
            name = normalize_name(value)
            if not name or name == 'Disease':
                raise ValueError(f'Invalid symptom name: {value!r}')
            if name in labels and labels[name] != value:
                raise ValueError(f'Ambiguous symptom names normalize to {name!r}. Review the source first.')
            labels[name] = value
            symptoms.add(name)
        if not symptoms:
            raise ValueError('A symptom profile must contain at least one recorded symptom.')
        symptom_counts.update(symptoms)
        lengths[len(symptoms)] += 1
        transactions.append(sorted([f'{name}=Yes' for name in symptoms] + [f"Disease={row['Disease']}"]))

    encoder = TransactionEncoder()
    matrix = pd.DataFrame(encoder.fit_transform(transactions), columns=encoder.columns_)
    mapping = [{'original_column': 'Symptom_1…Symptom_17', 'original_value': value,
                'transformed_column': name, 'new_item_label': f'{name}=Yes',
                'reason': 'Recorded presence; unlisted symptoms contribute no item'}
               for name, value in sorted(labels.items())]
    mapping += [{'original_column': 'Disease', 'original_value': value, 'transformed_column': 'Disease',
                 'new_item_label': f'Disease={value}', 'reason': 'Trimmed source disease label'}
                for value in sorted(frame['Disease'].unique())]
    log = {
        'original_rows': len(raw), 'cleaned_rows': len(frame),
        'duplicate_rows_removed': len(raw) - len(frame),
        'missing_values_before': quality['missing_values'],
        'missing_values_after': int(frame[slots].eq('').sum().sum()),
        'invalid_values_fixed': 0, 'invalid_value_details': [],
        'columns_removed': [], 'columns_excluded_from_mining': [],
        'columns_transformed': {slot: 'recorded symptom items' for slot in slots},
        'decisions': DECISIONS,
        'duplicate_policy': 'remove exact duplicates' if remove_duplicates else 'retain all rows',
    }
    distributions = {
        'Disease': frame['Disease'].value_counts().to_dict(),
        'Recorded_symptoms': dict(sorted(symptom_counts.items(), key=lambda item: (-item[1], item[0]))),
        'Symptoms_per_profile': {str(size): count for size, count in sorted(lengths.items())},
    }
    return frame, quality, log, transactions, matrix, mapping, distributions


def run_symptom_pipeline(config, root, raw_path):
    spec = dataset_spec('symptoms')
    if config.max_itemset_size > spec['max_itemset_size']:
        raise ValueError('The symptom dataset supports combinations up to 3 items to keep its larger symptom search practical.')
    root, raw_path = Path(root), Path(raw_path)
    raw = load_raw(raw_path)
    frame, quality, log, transactions, matrix, mapping, distributions = prepare_symptoms(raw, config.remove_duplicates)
    itemsets, rules, disease, counts = mine(matrix, config)
    summary = {
        'title': 'Association Rule Mining using Apriori on Recorded Disease Symptoms',
        'raw_records': len(raw), 'records': len(frame), 'attributes': len(raw.columns),
        'cleaned_attributes': len(frame.columns), 'mining_features': len(distributions['Recorded_symptoms']) + 1,
        'disease_classes': int(frame['Disease'].nunique()),
        'missing_values': quality['missing_values'], 'duplicate_records': quality['duplicate_rows'],
        'frequent_itemsets': len(itemsets), 'association_rules': len(rules), 'disease_rules': len(disease),
        'strong_rules': sum(rule['lift'] > 1 and rule['confidence'] >= .7 for rule in rules),
        'strong_rule_definition': 'confidence >= 0.70 and lift > 1 among exported rules',
        'distinct_items': len(matrix.columns), 'minimum_count': math.ceil(config.min_support * len(frame) - 1e-12),
        'generated_at': datetime.now(timezone.utc).isoformat(), 'raw_sha256': sha256(raw_path.read_bytes()).hexdigest(),
        'source': spec['source'], 'notice': NOTICE, **counts,
    }
    result = {
        'dataset': spec, 'summary': summary, 'config': config.model_dump(), 'quality': quality, 'cleaning': log,
        'distributions': distributions, 'itemsets': itemsets, 'rules': rules, 'disease_rules': disease,
        'symptoms': sorted(distributions['Recorded_symptoms']),
        'symptom_counts': distributions['Recorded_symptoms'], 'mapping': mapping,
    }
    for folder in ['results', 'data/processed', 'data/intermediate', 'reports']:
        (root / folder).mkdir(parents=True, exist_ok=True)
    frame.to_csv(root / 'data/processed/cleaned_dataset.csv', index=False)
    save_json(root / 'data/intermediate/transactions.json', transactions)
    pd.DataFrame({'transaction_id': range(1, len(transactions) + 1),
                  'items': [json.dumps(items) for items in transactions]}).to_csv(root / 'data/intermediate/transactions.csv', index=False)
    matrix.to_csv(root / 'data/intermediate/encoded_transactions.csv', index=False)
    for name, rows, fields in [
        ('frequent_itemsets', itemsets, ['itemset', 'support', 'item_count', 'length']),
        ('association_rules', rules, ['antecedents', 'consequents', 'support', 'confidence', 'lift']),
        ('disease_rules', disease, ['antecedents', 'consequents', 'support', 'confidence', 'lift']),
    ]:
        write_csv(root / f'results/{name}.csv', rows, fields)
    for name, value in [
        ('summary', summary), ('data_quality', quality),
        ('preprocessing_metadata', {'cleaning_log': log, 'feature_mapping': mapping}),
        ('analysis_config', config.model_dump()), ('analysis', result),
    ]:
        path = root / f'results/{name}.json'
        if name == 'analysis':
            # Keep both the API snapshot and its JSON attachment practical on hosted deployments.
            path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')), encoding='utf-8')
        else:
            save_json(path, value)
    return result
