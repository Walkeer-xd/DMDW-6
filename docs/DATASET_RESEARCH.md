# Kaggle datasets for broader disease associations

> Research record: the recommended itachi9604 source is now integrated as **Extended · Symptoms & diseases**. See [its workspace](../datasets/symptoms/README.md) and [current validation](../reports/DATASET_AND_VISUAL_VALIDATION.md). The standalone comparisons below document the selection rationale.

The current application mines associations with Apriori; it does not train a diagnostic classifier. Research below used public Kaggle downloads and metadata. Experiments ran separately and did not replace the application's source dataset, saved analysis, or report.

## Recommended sources

| Dataset | Verified content | Fit |
| --- | --- | --- |
| [Disease Symptom Prediction — itachi9604](https://www.kaggle.com/datasets/itachi9604/disease-symptom-description-dataset) | `dataset.csv`: 4,920 rows, 41 disease labels, `Disease` and `Symptom_1`–`Symptom_17`. Download also includes descriptions, severity weights, and precautions. | Best first addition: convert each row's nonempty symptom slots to a transaction with its disease label. The downloaded observations contain 131 distinct symptom names after trimming whitespace. |
| [Disease Prediction Using Machine Learning — kaushil268](https://www.kaggle.com/datasets/kaushil268/disease-prediction-using-machine-learning) | `Training.csv`: 4,920 rows, 132 binary symptom columns, `prognosis`, and an empty unnamed column. `Testing.csv`: 42 rows. The downloaded training file has 41 disease labels, although its card advertises 42 diseases. | Convenient alternative to the first source: map `prognosis` to Disease and convert present symptoms to items. Drop the empty column. |
| [Disease-Symptom Dataset — dhivyeshrk](https://www.kaggle.com/datasets/dhivyeshrk/diseases-and-symptoms-dataset) | Kaggle publisher metadata states 773 diseases, 377 one-hot symptoms, and approximately 246,000 rows. Metadata reports approximately 191 MB uncompressed. | Broader second source for an explicitly synthetic academic experiment. Its publisher states that the data was artificially generated. The large CSV was not downloaded or benchmarked in this research. |

Kaggle metadata was retrieved from `/api/v1/datasets/view/<owner>/<slug>`. Publisher-listed licenses are CC BY-SA 4.0 for itachi9604; “Database: Open Database, Contents: Database Contents” for kaushil268; and “World Bank Dataset Terms of Use” for dhivyeshrk. Preserve attribution and the source-specific license when redistributing imported files. The unusual third license label is publisher metadata, not independent verification of ownership or clinical provenance.

### Do not count overlapping sources as independent evidence

Both downloaded 4,920-row datasets contain 4,616 exact duplicate rows, leaving 304 distinct rows each. After translating their different schemas into sorted, trimmed symptom/disease transactions, 297 of the 304 unique transactions overlap. They should be treated as alternative representations of substantially overlapping data, not concatenated to create an apparently larger independent sample.

Likewise, the severity, description, and precaution files are reference tables; they should not be appended as observed patient profiles. Their content was not used in the Apriori experiment.

## Isolated Apriori checks

### Existing patient-profile source

Using the project's current cleaning and mining functions, max itemset size 4, confidence 30%, lift 1.20, and exact duplicate removal:

| Minimum support | Disease-oriented rules | Distinct disease labels |
| ---: | ---: | ---: |
| 2% | 12 | 1: Asthma |
| 1% | 42 | 4: Asthma, Hypertension, Pneumonia, Stroke |
| 0.5% | 56 | 8: the above, Bronchitis, COPD, Eczema, Psoriasis |

The current support floor is six of the 300 retained records. Rarer disease combinations fail that floor or the confidence/lift requirements. Asthma is not hardcoded as the only output. Lower thresholds can expose more labels but also admit patterns supported by only two or three records.

### itachi9604 symptom-list source

The downloaded `dataset.csv` was deduplicated to 304 profiles. Each transaction contained its disease plus its nonempty, trimmed symptom names. This experiment mined **present symptoms only**, used the existing `mine` function, and set max itemset size to **3** (at most two symptoms plus a disease), confidence to **30%**, and lift to **1.20**.

| Minimum support | Disease-oriented rules | Distinct disease labels |
| ---: | ---: | ---: |
| 2% | 891 | 19 |
| 1% | 1,166 | 40 |

The 1% result includes Dengue, Malaria, Diabetes, Migraine, Typhoid, Pneumonia, Tuberculosis, and several hepatitis labels. Counts describe this benchmark's internal associations, not diagnostic performance. These are standalone dataset results, not results from pooling the source with the original profiles.

## Required integration work

The current `src/pipeline.py` importer requires Age, Gender, Blood Pressure, Cholesterol Level, and four fixed symptoms. It cannot load these symptom-only sources unchanged.

1. Add source-specific adapters and metadata rather than manufacturing missing demographics or replacing the raw course dataset.
2. Represent available symptoms dynamically. For symptom-list sources, an unlisted symptom is not automatically a recorded negative; keep it unobserved. For binary sources, retain the source's semantics and avoid mining hundreds of common absence items by default.
3. Start with itachi9604 as a separately selectable analysis. Keep source provenance and results distinct; offer cross-source comparison before any pooled analysis.
4. Make symptom controls, summaries, dataset charts, and report methodology depend on each source's available fields.
5. Use explicit source-aware terminology and a documented duplicate policy. Keep the distinction between repeated benchmark patterns and independently observed profiles visible.
6. Tune support to dataset distribution. More disease classes alone do not ensure more qualifying disease rules: global support excludes any disease rarer than that floor. For a much broader source, evaluate disease-focused candidate generation or an explicit minimum-count mode rather than merely raising the export cap.

A sensible first demo extension is the original dataset plus a separately selectable symptom-list dataset. The isolated results above demonstrate broader coverage without creating artificial patient records or treating overlapping sources as independent observations.
