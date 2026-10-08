# Faculty usability update · validation

Date: 8 October 2026 (Asia/Kolkata).

## Automated checks

- Existing Python pipeline and API suite: **59 passed**, 27.50 seconds.
- One upstream Starlette/httpx deprecation warning; no failed tests.
- Production frontend build: **passed**, including the final contrast and navigation refinements.
- Default analysis rerun through the browser: completed, report regenerated, controls disabled while running and re-enabled afterwards.
- Verified current defaults: support 0.02, confidence 0.30, 300 retained profiles, 2,209 itemsets, 3,826 general rules, 12 disease rules.
- Original raw CSV SHA-256 preserved: `79cd5314cfdefec9b86ee0efd63d3df64a619a2e2511c5908abde008edf1bfa8`.

## Browser checks

- Welcome page opens first; the tutorial starts and progresses through all six steps.
- Tutorial links open the relevant section; returning preserves the current step.
- Previous/next controls, finish state, and restart entry point are present.
- How to use section map, glossary and expandable FAQ render correctly.
- Search for `Fever=Yes`: 976 matching rules. Adding a 70% confidence filter: 215 rules. Export URL correctly serializes confidence as 0.7. Reset restores 3,826 rules.
- Advanced rule metrics toggle; basic table defaults to count, support, confidence and lift.
- Duplicate-policy count preview changes from 6 to 7 at 2% support when retaining all 349 rows; restored before rerun.
- All nine original dashboard sections open; no browser console errors during the final route sweep.
- Selecting Acne shows 0 matching disease rules without a crash.
- PDF report successfully downloaded from the report page.
- 390 × 844 mobile viewport: welcome content fits, navigation opens, tutorial is usable; no horizontal document overflow observed.
- Dark-theme text contrast corrected and checked. Closed mobile navigation is hidden from keyboard/accessibility navigation.
- Desktop viewport and light theme restored for delivery.

## Evidence

- [Welcome screenshot](screenshots/faculty-welcome.jpg)
- [Mobile dark-theme screenshot](screenshots/faculty-mobile-dark.jpg)

The existing `VALIDATION.md` and older screenshots document the original project, not this revision. This revision preserves the analytical method and source data. New-machine dependency installation was not exercised on a separate clean computer; the included environment was used for testing. The portable ZIP excludes machine-specific environments and includes the built frontend, dataset and results.
