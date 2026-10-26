# Extended symptom dataset

This is a separate analysis workspace. Its files do not replace the original course dataset, results, or reports at the repository root.

Source: [Disease Symptom Prediction](https://www.kaggle.com/datasets/itachi9604/disease-symptom-description-dataset), published by **itachi9604**, Kaggle version 2. The publisher credits assistance from Pratik Rathod. Kaggle lists **[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)**. Preserve this attribution and source license with redistributed material.

`data/raw/dataset.csv` is the original file extracted byte-for-byte from the public Kaggle archive. The acquisition manifest contains its SHA-256, version, source URL, date, and license metadata. Source clinical provenance is unverified; this is an educational benchmark, not a validated diagnostic dataset.

The source has 4,920 rows and 41 disease labels, with up to 17 listed symptoms per row. Exact-duplicate removal retains 304 distinct source profiles and 131 distinct symptom types. Repeated benchmark rows are not independent patient observations.

Only listed symptoms create `symptom_name=Yes` items. Unlisted symptoms are unobserved, never converted to No. No demographic or outcome fields are invented. The supplemental severity, description, and precaution files were not incorporated as patient observations.

Default analysis: **1% support, 30% confidence, lift 1.20, maximum itemset size 3, 5,000 exported general rules, 5,000 exported disease rules, exact-duplicate removal**. The independent caps retain all 1,166 qualifying disease rules, covering 40 of 41 labels. There are 21,092 qualifying general rules before the general-rule export cap. No-match diseases remain available in the dataset selector/filter and are explained as having no qualifying rule.

To regenerate only this workspace with the project's Python environment:

```bash
python scripts/run_pipeline.py --dataset symptoms
```

The original command without `--dataset` continues to operate on the original patient-profile source. In the app, each Run analysis button acts on the dataset selected above it. Switching datasets only reads their saved snapshots.

Derived files are under `data/processed/`, `data/intermediate/`, `results/`, `reports/`, and `REPORT.md` inside this workspace. Cleaned labels are trimmed; raw source spellings remain in the immutable input. Reports, CSVs, and API snapshots describe only this source's analysis.
