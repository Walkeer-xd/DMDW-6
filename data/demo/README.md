# Presentation datasets

These CSVs are **synthetic, fictional teaching examples**, generated for the live
upload demo. They contain no real patient records and are not evidence about disease.

- `presentation_profiles.csv`: 63 rows, 10 columns, three fictional disease groups.
  Includes three exact duplicates, an invalid age, an empty symptom observation and
  a value with inconsistent case/spacing to demonstrate auditing and cleaning.
- `presentation_symptoms.csv`: 63 rows, 18 columns (`Disease`, `Symptom_1` through
  `Symptom_17`), the same three fictional groups and three exact duplicate rows.
  Empty symptom slots contribute no transaction item.

Open **Live upload demo** in Association Lab. Download either sample from that page,
select it and press **Run live analysis**. Default settings retain 60 rows and produce
rules for all three disease groups. Expand each completed processing stage to inspect
the first five source/cleaned records, transactions, binary matrix and itemsets.

Try keeping every source row, or changing minimum support, confidence or lift, then
run again to show how the evidence and rules change. The maximum combination size
is three and each rule family is capped at 5,000 rules for responsive presentations.

Download cleaned rows, transactions, frequent itemsets, all rules, disease rules and
the complete analysis JSON from the results. Uploads use request-specific temporary
server directories that are removed on completion or failure. Results live only in
the current browser tab's memory; **Clear demo** or a page refresh discards them.
Saved source datasets and their prepared analyses are never overwritten by this flow.
