"""Known data sources and their independent analysis workspaces."""
from pathlib import Path

from src.pipeline import AnalysisConfig, SOURCE

DEFAULT_DATASET = 'profiles'
DATASETS = {
    'profiles': {
        'id': 'profiles',
        'name': 'Original · Patient profiles',
        'title': 'Disease Symptoms and Patient Profile',
        'description': 'Four recorded symptoms and demographic details. The original course dataset.',
        'has_demographics': True,
        'source': SOURCE,
        'source_label': 'Kaggle / uom190346a / version 2',
        'license': 'MIT (as listed by the publisher)',
        'acquired_date': '2026-10-02',
        'record_label': 'retained profiles',
        'search_example': 'Fever=Yes',
        'max_itemset_size': 5,
        'default_config': AnalysisConfig().model_dump(),
    },
    'symptoms': {
        'id': 'symptoms',
        'name': 'Extended · Symptoms & diseases',
        'title': 'Disease Symptom Prediction',
        'description': '41 disease labels and 131 recorded symptom types. Symptoms only; demographics are not supplied.',
        'has_demographics': False,
        'source': 'https://www.kaggle.com/datasets/itachi9604/disease-symptom-description-dataset',
        'source_label': 'Kaggle / itachi9604 / version 2',
        'license': 'CC BY-SA 4.0 (as listed by the publisher)',
        'acquired_date': '2026-10-26',
        'record_label': 'retained symptom profiles',
        'search_example': 'skin_rash=Yes',
        'max_itemset_size': 3,
        'default_config': AnalysisConfig(min_support=.01, max_itemset_size=3, max_rules=5000).model_dump(),
    },
}


def dataset_spec(dataset_id):
    if dataset_id not in DATASETS:
        raise ValueError('Unknown dataset. Choose profiles or symptoms.')
    return DATASETS[dataset_id]


def dataset_root(root, dataset_id):
    dataset_spec(dataset_id)  # Validate before constructing any filesystem path.
    return Path(root) if dataset_id == DEFAULT_DATASET else Path(root) / 'datasets' / dataset_id
