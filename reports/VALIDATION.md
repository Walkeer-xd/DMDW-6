# Validation record

Completed on 2 October 2026 (Asia/Kolkata).

## Executed checks

- **59 automated tests passed** on the final analysis/report code. Machine-readable results: `reports/test-results.xml`. The final run took 57.79 seconds.
- **Frontend production build passed**, with no build warnings after bundle splitting. The built website is included in `frontend/dist/`.
- **Python syntax compilation passed** for `src`, `backend` and `scripts`.
- **Raw source integrity passed:** SHA-256 `79cd5314cfdefec9b86ee0efd63d3df64a619a2e2511c5908abde008edf1bfa8`. A second, version-specific Kaggle download independently matched these bytes. Running the download script with the local file present preserved it.
- **Pipeline executed**, producing 300 retained profiles from 349 raw rows, 2,209 itemsets, 3,826 general rules and 12 disease-oriented rules at the default parameters.
- **Reproducibility passed:** two independent full pipeline runs produced equal ordered analysis results (excluding timestamp) and byte-identical principal CSV/metadata exports.
- **Metric verification passed:** support, confidence and lift for every real exported rule were independently recomputed from Boolean transaction membership; hand-counted unit-test baskets also confirmed leverage and conviction.
- **All API routes and eight export variants passed**; invalid parameters, empty results, exact disease filters, concurrent-run rejection and a complete staged rerun were tested.
- **Dashboard-triggered full rerun passed:** the UI showed Analysis running and disabled the run button, then refreshed the completed snapshot and generated report without a browser reload.
- **All nine dashboard sections rendered** through the browser, including charts, audit details, itemsets, both rule families, parameters and report exports.
- **Browser interactions passed:** disease selection, pattern search, zero-match empty state, reset, metric sorting, mobile navigation and light/dark switching.
- **Responsive checks passed:** desktop at the normal browser size; mobile 390 x 844; tablet 820 x 1180. No document-level horizontal overflow was observed in overview at the tested mobile/tablet sizes. Wide data tables intentionally use their own horizontal scroll region.
- **Browser console errors:** none observed during the tested flows.
- **PDF visual review passed:** all six final pages rendered and inspected; title page, tables, charts, paragraphs and page numbering are readable with no observed clipping or overlap. The rule table continues with a repeated header.

## Evidence

`reports/screenshots/` contains desktop overview, disease analysis, mobile overview, tablet overview and dark-theme screenshots. The final PDF is `reports/DMDW6_Report.pdf`. Source provenance is recorded in `data/raw/provenance.json`.

## Non-blocking dependency notice

The test runner emits one Starlette deprecation warning about its httpx-based TestClient. Tests and API responses pass; this is a dependency migration notice, not an application failure. Package versions are frozen in requirements.txt.

## Scope limits

These checks verify the implementation and the recorded data, not medical validity or universal absence of defects. No clinical validation, causal claim, external holdout evaluation or significance testing is asserted. The default disease rules cover Asthma only; this is the actual threshold-dependent result. The optional notebook is provided as an interactive walkthrough; shipped results are generated and validated through the scripts.
