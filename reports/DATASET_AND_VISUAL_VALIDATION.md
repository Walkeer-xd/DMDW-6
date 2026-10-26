# Dataset selection and visual exploration — validation

## Delivered behavior

- The original course dataset remains the default. Its raw CSV, intermediate files, saved results, and generated report are unchanged.
- The separately selectable symptom source has 4,920 original rows, 304 retained profiles, 131 observed symptom types, 41 labels, and 1,166 qualifying disease rules covering 40 labels at its defaults.
- Source-specific charts, tutorials, defaults, reruns, filtered CSVs, and complete downloads follow the selected dataset.
- The main pages use coverage/evidence visuals and short labels. Methodology, audit details, explanations, and exact chart metrics remain available on demand.
- Filters use native menus populated from the selected analysis. Condition filtering and filtered CSV match the same exact item. Active chips can be removed independently.
- Ranked bars show the complete association. Lift and confidence rankings share a switchable view; chart disease selection applies to scatter plots and rankings.
- Rule and combination tables show 10 selected rows per page. Pagination changes only the visible page, while CSV retains the full selected limit and sort order.
- Analysis settings starts with preset menus and retains precise numeric entry through Custom values.

## Automated and browser verification

- Production frontend builds passed with Vite 7.3.7. The patch update reported zero npm vulnerabilities.
- The API and dataset suite passed **67 tests**, including source identity, symptom semantics, independent rule counts, per-source defaults, exports, hosted payload sizes, exact condition selection, failed-run isolation, and a real staged rerun in a temporary workspace.
- Chrome checks against the built frontend and real API passed for both sources:
  - All 12 sections at 1440, 768, 390, and 320 CSS pixels without page-level horizontal overflow.
  - Condition/disease/category/combination menus; threshold presets; row limits; active-chip removal; reset; sorting; optional metrics; pagination; and filtered CSV parity.
  - Full association labels, disease-scoped charts, lift/confidence switching, empty-state handling, and expandable explanations/audits.
  - Dataset-specific parameter presets, custom numeric values, restore defaults, and all six tutorial steps.
  - All seven complete downloads and a real rerun of only the extended source using the preset interface.
  - Light/dark themes and no JavaScript page errors.
- After the real extended-source rerun, the original API snapshot still matched the pre-run snapshot. SHA-256 comparison confirmed **all 18 original source, intermediate, result, PDF, and figure files were unchanged**.
- The prepared extended JSON snapshot and all its attachment endpoints fit the tested 4,500,000-byte payload budget. Its disease-rule family is not truncated by the independent 5,000-rule cap.
- `git diff --check` passed.

## Existing complete-suite issue

The complete Python suite during integration finished with **96 passed and one pre-existing failure** in `test_source_identity_and_loading`. That test expects the original CSV's CRLF checksum, while the committed checkout uses LF. The subsequent exact-condition regression is included in the 67 passing API/dataset tests above.

Original committed and working-file SHA-256: `51a5ad0bd29dce904b3d74b66e93ca10fbcbbb0b23f57235f8ba1f4debe33c50`.

Its CRLF representation matches the test's expected checksum: `79cd5314cfdefec9b86ee0efd63d3df64a619a2e2511c5908abde008edf1bfa8`.

The original source and its saved outputs were intentionally not altered to address this pre-existing test issue. QA used temporary Python and Playwright packages under `/tmp`; project Python dependency files were not changed.

## Review artifacts

- `reports/screenshots/presentation-welcome.jpg`
- `reports/screenshots/symptom-dataset-overview.jpg`
- `reports/screenshots/named-association-charts.jpg`
- `docs/PRESENTATION_GUIDE.md`
- `datasets/symptoms/README.md` and its raw-source provenance manifest
