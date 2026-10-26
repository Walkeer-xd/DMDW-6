"""Regenerate one dataset's analysis and report without changing other sources."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pipeline import ROOT, AnalysisConfig, run_pipeline
from src.datasets import DATASETS, dataset_spec, dataset_root
from src.symptom_pipeline import run_symptom_pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', choices=DATASETS, default='profiles')
    parser.add_argument('--min-support', type=float)
    parser.add_argument('--min-confidence', type=float)
    parser.add_argument('--min-lift', type=float)
    parser.add_argument('--max-itemset-size', type=int)
    parser.add_argument('--max-rules', type=int)
    parser.add_argument('--keep-duplicates', action='store_true')
    args = vars(parser.parse_args())
    selected = args.pop('dataset')
    args['remove_duplicates'] = not args.pop('keep_duplicates')
    config = AnalysisConfig(**{**dataset_spec(selected)['default_config'], **{key: value for key, value in args.items() if value is not None}})
    destination = dataset_root(ROOT, selected)
    if selected == 'profiles':
        result = run_pipeline(config, root=destination)
    else:
        result = run_symptom_pipeline(config, root=destination, raw_path=destination / 'data/raw/dataset.csv')
    from src.reporting import generate_report
    generate_report(result, root=destination)
    print({'dataset': selected, **{key: result['summary'][key] for key in ['raw_records', 'records', 'frequent_itemsets', 'association_rules', 'disease_rules']}})


if __name__ == '__main__':
    main()
