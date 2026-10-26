# Frontend presentation refresh — validation

For the subsequent dataset integration and simplified visual interface, see [the current validation record](DATASET_AND_VISUAL_VALIDATION.md).

The frontend keeps the existing dataset, analysis, filters, tutorial, charts, parameter controls, and export routes. The new visual system covers all 12 sections, adds grouped navigation and section search, and includes local variable fonts and their licenses. The home diagram uses the leading disease rule from the current API response; its evidence is not invented.

## Checks completed

- Production build: `npm --prefix frontend run build` passed with Vite 7.3.7.
- Dependency installation/audit after the compatible Vite patch: zero reported vulnerabilities.
- Browser checks against the real FastAPI backend and built frontend using installed Chrome and temporary Playwright tools:
  - All 12 sections rendered at 1440, 1280, 1024, 768, 390, and 320 CSS pixels, with no page-level horizontal overflow. Wide tables scroll inside their containers.
  - Rule search, empty states, reset, advanced thresholds, sorting, and optional metrics passed.
  - Disease selection, category exploration, and frequent-combination search passed.
  - All six tutorial steps, visits to the working sections, returning to the tutorial, and completion passed.
  - Section search, Ctrl+K, keyboard focus containment, and Escape passed.
  - Parameter editing and restoring defaults passed. Browser verification did not replace the prepared analysis.
  - All seven complete export endpoints returned successful attachments; the PDF downloaded through the UI.
  - Light/dark switching passed.
  - No JavaScript page errors or third-party requests were observed. Fonts load from the local application.
- `git diff --check` passed.

## Existing Python suite

The existing suite completed with **58 passed, 1 failed** in a temporary Python QA environment. The failure is `test_source_identity_and_loading`, which expects the source CSV's CRLF checksum. The checkout contains LF line endings.

- Current and committed file SHA-256: `51a5ad0bd29dce904b3d74b66e93ca10fbcbbb0b23f57235f8ba1f4debe33c50`
- CRLF representation SHA-256 (expected by the existing test): `79cd5314cfdefec9b86ee0efd63d3df64a619a2e2511c5908abde008edf1bfa8`

The source file is byte-for-byte identical to `HEAD`. No dataset, pipeline, report calculation, or backend source was changed. The passing tests include the API export checks and an isolated analysis rerun/report-generation check. Temporary QA packages were installed under `/tmp`, without changing the project's Python dependency files.

## Presentation assets

- Opening screen: `reports/screenshots/presentation-welcome.jpg`
- Walkthrough: `docs/PRESENTATION_GUIDE.md`
