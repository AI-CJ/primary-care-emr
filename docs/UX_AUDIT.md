# UX redesign release audit

**Audit date:** 24 November 2026 (Eastern time)  
**Pre-sprint baseline:** `fb656cbe79d4a54bab062d22b8e8b13c2aa13313`  
**Audited implementation:** `c14b57310902f1c5fbd70f84b313a1ecbc72f353`  
**Disposition:** Implementation checks passed; this documentation commit and its eventual merge still require verification before release.

This is an engineering audit of an educational EMR, not a clinical safety certification, security penetration test, or declaration of WCAG conformance. Use fictional records only.

## Scope and changes

The [complete implementation diff](https://github.com/AI-CJ/primary-care-emr/compare/fb656cbe79d4a54bab062d22b8e8b13c2aa13313...c14b57310902f1c5fbd70f84b313a1ecbc72f353) contains 32 files (951 additions, 260 deletions), including three new frontend unit-test files and expanded existing browser smoke tests. The review covered the changed sign-in, brand artwork, navigation, dashboard, patient chart, documentation and portal components; corresponding styles, record grouping functions and test changes. The existing backend, migration files, dependency manifests and deployment workflow are unchanged in this diff. This is not a line-by-line inspection of every unchanged file.

| Milestone | Evidence |
| --- | --- |
| Staff and patient entry, dashboard and home | [PR 74](https://github.com/AI-CJ/primary-care-emr/pull/74) |
| Chart identity, recorded allergy status, clinical snapshot and visit notes | [PR 75](https://github.com/AI-CJ/primary-care-emr/pull/75) |
| Patient navigation, appointment history, preferences and released results | [PR 76](https://github.com/AI-CJ/primary-care-emr/pull/76) |
| Browser startup preparation and timing regression | [PR 77](https://github.com/AI-CJ/primary-care-emr/pull/77), [implementation commit](https://github.com/AI-CJ/primary-care-emr/commit/c14b57310902f1c5fbd70f84b313a1ecbc72f353) |

## Reproducible verification

All five jobs passed for the exact audited implementation in [Checks 45545585324](https://github.com/AI-CJ/primary-care-emr/actions/runs/45545585324). The earlier merged redesign also passed [Checks 45542429194](https://github.com/AI-CJ/primary-care-emr/actions/runs/45542429194). Reproduce with the setup and disposable database configuration in [checks.yml](../.github/workflows/checks.yml); never run destructive smoke tests against a real patient database.

| Job | Commands and observed outcome |
| --- | --- |
| backend-tests | `alembic upgrade head`, `alembic current`, `python -m unittest discover -s backend/tests -p 'test_*.py'` — migration step passed; 376 tests passed |
| frontend-build | In frontend: `npm ci`, `npm run lint`, `npm test`, `npm run build` — 33 tests passed, zero failures, lint/build successful |
| public-demo-smoke | Static demo file and notice checks, `python scripts/check_demo_contrast.py`, `scripts/check_demo_browser.py` — passed; legacy static demo exercised at 360 and 1280 CSS pixels, not a substitute for the React application |
| api-browser-smoke | Disposable PostgreSQL migration and seed, React build, running API and UI, `python -m scripts.check_app_browser` — passed |
| interactive-browser-smoke | `python scripts/build_browser_runtime.py`, build with `VITE_EMR_BROWSER=1`, serve the generated application under the Pages base path, `python scripts/check_browser_emr.py`, `python scripts/check_browser_clinical_api.py` — both smoke scripts passed |

The CI jobs actually build and exercise the React application in Chromium, not only static source checks. Individual log evidence: [backend](https://github.com/AI-CJ/primary-care-emr/actions/runs/45545585324/job/138974278391), [frontend](https://github.com/AI-CJ/primary-care-emr/actions/runs/45545585324/job/138974277984), [PostgreSQL-backed browser](https://github.com/AI-CJ/primary-care-emr/actions/runs/45545585324/job/138974278494), [isolated browser workspace](https://github.com/AI-CJ/primary-care-emr/actions/runs/45545585324/job/138974278267).

### Functional and safety-oriented coverage

| Area | Checked behavior and limits |
| --- | --- |
| Staff dashboard and directory | Dashboard appears after staff sign-in; schedule count is numeric and the patient-search action opens the directory; existing search, schedule and chart navigation remain exercised. Not every dashboard tile was individually browser-clicked. |
| Patient chart | Correct selected patient heading, recorded conditions and medications, latest vital selection, empty newly created chart, allergy creation, severity and reaction display, transition to historical-only status, archive and restore. Source review confirms chart-scoped API requests and no fabricated clearance when records are empty. |
| Documentation | Unsaved form navigation protection; standalone note draft, confirmation checkbox, finalization and no edit control after finalization; appointment-linked note and clinical API lifecycle covered in packaged API smoke. |
| Patient portal | Home and upcoming-care heading, health information, request history, preferences save and persistence, keyboard activation and focus transfer. Unit tests cover open/closed appointment grouping, midnight/noon labels, earlier released result history and exclusion of null/unreleased results from released grouping. API smoke verifies lab result unavailable before release and available after release. |
| Care coordination | Packaged clinical API smoke covers orders, linked notes, finalization, lab release, referrals, goals, follow-ups and appointment-change requests. Existing backend tests cover validation and authorization for individual routes. |
| Account boundaries | Both staff and patient modes, role-specific staff controls, wrong-role rejection, session termination, patient ownership and denied cross-role API access are exercised by backend and browser checks. Password verification is unchanged. |
| Persistence and reset | Within-tab edits, preferences, audit CSV export, independent browser context, cancelled reset and confirmed reset restoring seed data; no shared database in browser mode. |
| Legal notice | Single notice remains visible; reset control stays in the notice in browser mode and is absent in API-backed mode. Sign-in switching remains labeled. A preparation failure refers users to the existing reset control rather than adding another control. |

Backend security tests cover invalid credentials, missing/expired sessions, account scope and denied routes. Existing browser tests do not cover every combination of invalid form input, slow requests, connection failures or assistive-technology behavior. New summary components distinguish loading, unavailable and empty states in source; comprehensive fault injection is outstanding.

### Accessibility and responsive layout

The API-backed Chromium script checks patient keyboard activation, heading focus after navigation, no horizontal overflow at the tested mobile layouts including 320 CSS pixels, and patient navigation button heights of at least 44 CSS pixels. The browser-only script exercises staff navigation at 360 CSS pixels and verifies no horizontal overflow on the tested staff screen. The original SVG artwork is decorative and has explicit accessibility attributes; textual button names remain present.

Source-level spot checks use sRGB relative luminance and the contrast ratio `(Lighter + 0.05) / (Darker + 0.05)`. Convert each 8-bit channel to 0–1, then to linear RGB (divide by 12.92 when the channel is at most 0.04045; otherwise raise (channel + 0.055) / 1.055 to 2.4); weight linear R/G/B by 0.2126/0.7152/0.0722. Nineteen sampled declared foreground/background pairs ranged from 4.91:1 to 12.33:1; examples below are reproducible from the colors in the changed CSS. Gradient endpoints were sampled where specified; these are not computed-style measurements across all possible rendered states.

| Sample | Foreground | Background | Ratio |
| --- | --- | --- | --- |
| Staff sign-in heading | #ffffff | #22383e | 12.33:1 |
| Patient sign-in heading | #214d41 | #d4eee3 | 7.78:1 |
| Patient sign-in body | #345d51 | #d4eee3 | 6.05:1 |
| Upcoming-care label at lighter gradient endpoint | #e2f4ed | #237463 | 4.91:1 |
| Active patient navigation | #ffffff | #1c6452 | 7.01:1 |
| Patient status label | #235b49 | #e9f4ed | 6.99:1 |
| Recorded allergy context | #743624 | #fff5ef | 8.52:1 |
| Draft status | #6e4b16 | #faf2e0 | 7.03:1 |
| Sign-in preparation status | #495d60 | #ffffff | 6.96:1 |

The reference target is [WCAG 2.2](https://www.w3.org/TR/WCAG22/), with a project goal of 4.5:1 for normal text and 44 CSS pixel patient controls. Browser checks and source samples do not establish complete accessibility. Independent screenshot inspection, screen-reader testing, full zoom/reflow testing, tablet-specific review and representative clinician/patient usability sessions remain outstanding. No task-time or click-count improvement is claimed without a measured baseline.

### Startup performance remediation

The existing public hosting mode initializes a local Python runtime and fictional SQLite database when the first browser API request arrives. Initialization includes loading FastAPI, SQLAlchemy and cryptography, unpacking the API source and seeding the database and accounts. The audited build prepares 18 pinned runtime packages totaling 19.4 MiB on disk before HTTP transfer compression. It does not use a remote clinical server.

The performance commit starts a request to the public root endpoint while the sign-in view is visible, with no credential submission or account session establishment, and reports preparation status. Sign-in remains available during preparation. The browser regression checks that preparation completes before sign-in without creating a signed-in session, then measures the prepared sign-in and exercises the clinical workflows, isolation and reset. The server-backed path and authentication parameters are unchanged.

Observed in [the browser-only job log](https://github.com/AI-CJ/primary-care-emr/actions/runs/45545585324/job/138974278267):

- Fresh-tab navigation to prepared workspace: **10.07 seconds**.
- Account sign-in after workspace preparation: **0.88 seconds**.

These are single observations on the local CI server, not production latency percentiles or a verified speedup against an instrumented old build. Preparation overlaps the time spent reading or entering credentials; it does not eliminate the startup cost if the user signs in immediately. Network/device variation, cold-cache public Pages timing, memory consumption and failure recovery have not been independently measured. Proper server-backed hosting remains an architectural option.

## Provenance and licensing

The added project-specific implementation is authored for this repository: inline SVG brand and task illustrations, original React components, CSS and regression tests. The review found no newly introduced image files, downloaded third-party artwork, external design kit, dependency manifest or lockfile change, or license change in the implementation diff. The existing framework/runtime dependencies remain third-party licensed software. GitHub reports the repository as public and does not identify a repository-level license. Neither repository visibility nor licensing was changed; do not infer exclusive ownership or independent legal clearance from this audit. Originality here means independent project-specific implementation and review of the changed source, not a comprehensive external similarity search.

Research is cited in [UX_DESIGN.md](UX_DESIGN.md), including [NIST health IT interface design](https://www.nist.gov/publications/technical-basis-user-interface-design-health-it) and WCAG 2.2. References inform design and verification goals rather than reproduce another product's screens, code or visual assets.

## Release verification

The already-merged patient portal redesign at `d4f724fbe4cc072a698d40b8046a1d9860643b22` passed all five jobs. Its [Pages deployment 45542706528](https://github.com/AI-CJ/primary-care-emr/actions/runs/45542706528) initially failed to locate the named artifact in GitHub's deployment service after build/upload. Retrying the failed deployment job succeeded on attempt 2. This was a deployment infrastructure issue, not a failing application test.

The audited implementation passed its own pre-merge CI. The final audit commit must pass the same checks, followed by verification of the actual merged SHA and its Pages deployment. This report cannot establish the success of a future deployment. Independent retrieval of the [public application](https://ai-cj.github.io/primary-care-emr/) was unsuccessful in the audit environment (web access unavailable and DNS resolution failed), so direct visual inspection of the public site was not possible. GitHub deployment status and CI browser execution are separate evidence, and neither is represented as an independent public-site inspection.

## Remaining limitations and release gate

- Preserve the educational-only scope, existing role checks and fictional data. Do not use this project to treat patients.
- No known failures in the five completed checks at the audited implementation SHA. Do not equate passing tests with absence of defects.
- Representative-user validation, screen-reader evaluation, complete accessibility/security audit, independent deployed-site screenshots and public-network latency benchmarks are not complete.
- Merge only after all checks succeed on the final review branch; verify the merge SHA and deploy it successfully. If either fails, keep the last verified release and report the failure instead of declaring the sprint complete.
