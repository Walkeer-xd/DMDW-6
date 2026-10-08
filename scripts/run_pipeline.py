"""One command regenerates the analysis, charts and academic report."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.pipeline import AnalysisConfig, run_pipeline

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--min-support',type=float,default=.02)
    parser.add_argument('--min-confidence',type=float,default=.30)
    parser.add_argument('--min-lift',type=float,default=1.20)
    parser.add_argument('--max-itemset-size',type=int,default=4)
    parser.add_argument('--max-rules',type=int,default=20000)
    parser.add_argument('--keep-duplicates',action='store_true')
    args=vars(parser.parse_args()); args['remove_duplicates']=not args.pop('keep_duplicates')
    result=run_pipeline(AnalysisConfig(**args))
    from src.reporting import generate_report
    generate_report(result)
    print({k:result['summary'][k] for k in ['raw_records','records','frequent_itemsets','association_rules','disease_rules']})

if __name__=='__main__': main()
