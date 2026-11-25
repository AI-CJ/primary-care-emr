# UX redesign release audit

**Audit date:** 24 November 2026 (Eastern time)  
**Pre-sprint baseline:** `fb656cbe79d4a54bab062d22b8e8b13c2aa13313`  
**Audited implementation:** `c14b57310902f1c5fbd70f84b313a1ecbc72f353`  
**Disposition:** Released. The audited implementation and original audit commit were verified, merged and deployed at [`5a52bb8`](https://github.com/AI-CJ/primary-care-emr/commit/5a52bb84e2e86148cd228e4239e47c696a5e0a24).  
**Release verification:** November 24, 2026, 11:25 PM Eastern.

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

The final audit commit, `3c01b84c67096eb2942150ede93d958d11233256`, passed [Checks 45545956327](https://github.com/AI-CJ/primary-care-emr/actions/runs/45545956327). [PR 77](https://github.com/AI-CJ/primary-care-emr/pull/77) merged the audited implementation and its report into main at `5a52bb84e2e86148cd228e4239e47c696a5e0a24`.

| Final release gate | Verified evidence |
| --- | --- |
| Merged implementation and audit | [PR 77](https://github.com/AI-CJ/primary-care-emr/pull/77) |
| Main verification | [Checks 45546235206](https://github.com/AI-CJ/primary-care-emr/actions/runs/45546235206): all five jobs passed |
| Main backend | [Job 138976427577](https://github.com/AI-CJ/primary-care-emr/actions/runs/45546235206/job/138976427577): migration step and 376 tests passed |
| Main frontend | [Job 138976427559](https://github.com/AI-CJ/primary-care-emr/actions/runs/45546235206/job/138976427559): lint, 33 tests and build passed |
| Main browser workspace | [Job 138976427451](https://github.com/AI-CJ/primary-care-emr/actions/runs/45546235206/job/138976427451): application workflow and packaged API tests passed |
| Pages deployment | [Run 45546500308](https://github.com/AI-CJ/primary-care-emr/actions/runs/45546500308): successful on attempt 1, November 24, 2026, 11:25 PM Eastern |

The final main browser job recorded 6.97 seconds for fresh-tab preparation and 0.39 seconds for sign-in after preparation. The pre-merge and post-merge timings are two local CI observations; neither establishes a production latency target.

Independent retrieval of the [public application](https://ai-cj.github.io/primary-care-emr/) was unsuccessful in the audit environment because direct network access was unavailable. The successful Pages deployment and the local Chromium test results establish different facts. Neither substitutes for independent inspection of the public site.

## Documentation follow-up

The root README, frontend guide, [workflow reference](WORKFLOWS.md), [original release record](V1_RELEASE.md) and design rationale now describe the same two execution modes, current role capabilities, startup behavior and verified release. The detailed API and lifecycle contracts were retained in the workflow reference. The browser smoke test gained optional reference screenshot capture, and CI archives those captures separately from the deployed application. No application components, styles, clinical behavior, dependency manifests or database migrations changed in this documentation follow-up.

The application release evidence above is tied to its verified SHA. The documentation and capture changes have their own CI run; they do not retroactively change the original V1 tag or claim a fresh deployment before that run completes.

## Remaining limitations

- Preserve the educational-only scope, existing role checks and fictional data. Do not use this project to treat patients.
- The five verification jobs passed at the audited implementation and merged release SHAs. Passing tests are not evidence that every defect has been found.
- The final main frontend installation reported **11 npm dependency advisories: nine moderate and two high**. See [frontend job 138976427559](https://github.com/AI-CJ/primary-care-emr/actions/runs/45546235206/job/138976427559). The sprint introduced no new application dependencies. Advisory details, affected dependency paths, exploitability and remediation remain unverified; a separate dependency review is required.
- Representative-user validation, screen-reader evaluation, complete accessibility/security audit, independent deployed-site screenshots and public-network latency benchmarks are not complete.
- Future releases should pass the same automated gates and verify the deployed commit. Keep the last verified application available if a new build fails. Do not treat archived local CI captures as direct public-site verification.


## Follow-up interface audit (November 25, 2026)

**Baseline:** `b5b8abf5aaa6fd467fe9b5ff48903c6c1b2f8a04`  
**Audited changes:** `0b2907d34d2fc89f48d5f746dd5fe1ebd11d20e2`  
**Review:** [PR 79](https://github.com/AI-CJ/primary-care-emr/pull/79), [passing verification](https://github.com/AI-CJ/primary-care-emr/actions/runs/45559505198).

The review used the six baseline Chromium screenshots from [Checks 45558339219](https://github.com/AI-CJ/primary-care-emr/actions/runs/45558339219) and seven new captures from the passing refinement build. The actual rendered screenshots were inspected, including both sign-in modes, staff dashboard, patient chart summary, patient home and mobile views. The captures were made using a locally served browser build with fictional starting records, not by independently accessing the public site.

| Full-page capture | Baseline height | Refined height | Viewport width |
| --- | ---: | ---: | ---: |
| Staff sign-in | 950 px | 900 px | 1280 px |
| Staff dashboard | 947 px | 902 px | 1280 px |
| Patient chart summary | 2168 px | 1584 px | 1280 px |
| Patient sign-in | 962 px | 900 px | 1280 px |
| Patient home | 1033 px | 956 px | 1280 px |
| Mobile patient home | 1795 px | 1666 px | 360 px |

These are full-page screenshot dimensions from the specific test records and viewports, not representative-user task measurements. The more compact chart summary retains all returned timeline entries through an explicit expansion control; it does not delete or omit them from the API. The staff chart also has a new 360 px capture. Its clinical content still requires vertical scrolling on narrow screens.

The visual pass introduced original shared SVG icons and adjusted spacing, card grids, typography and status feedback. The interaction pass corrected mobile chart-to-directory navigation, avoids loading the directory before it is visited, moves keyboard focus to staff destinations without overriding linked-appointment or note focus, preserves unsaved staff and patient edits when sign-out is cancelled, prioritizes the upcoming visit on patient home, and labels bounded request counts without implying an exact total.

All five jobs passed at the audited revision. PostgreSQL migrations and 376 backend tests passed; frontend lint, 34 tests and production build passed. Browser tests exercised all six dashboard queue destinations, timeline expansion/collapse, staff focus, patient focus, mobile chart navigation, clearing search, unsaved staff sign-out cancellation, hidden patient preference draft cancellation, preference save state, clinical workflows and reset. The browser-only clinical API smoke also passed. The seven PNGs were uploaded as the `emr-workspace-screenshots` artifact (ID 14997770476, retained for 30 days).

The browser run measured 7.01 seconds for preparation and 0.41 seconds for prepared sign-in on its local CI server. This is another observation, not a production benchmark. No application dependency, database migration, or clinical API contract changed. Existing npm installation warnings still report nine moderate and two high advisories; remediation and production exposure assessment remain outstanding. This pass does not establish complete accessibility, usability, security or clinical certification. Screen-reader, representative-user and independent public-network checks remain open. The audited branch and subsequent deployment must pass their release gates before the refinements are published.


## Dependency and accessibility follow-up (November 25, 2026)

The refinement merge at [47d6d7b](https://github.com/AI-CJ/primary-care-emr/commit/47d6d7b4386de3b1a8ac2ebfbaca9e6a573102ae) passed [main Checks](https://github.com/AI-CJ/primary-care-emr/actions/runs/45560346481) and [Pages deployment](https://github.com/AI-CJ/primary-care-emr/actions/runs/45560669542). This resolves the earlier outstanding deployment status for PR 79.

The [initial dependency review](https://github.com/AI-CJ/primary-care-emr/actions/runs/45560758733) found 11 affected npm dependency nodes (nine moderate, two high). The production-only scan was clean. The direct advisories involved Vite's development server/editor behavior, minimatch's glob processing and Zod's constrained collection validation; other reported nodes inherited vulnerable dependencies. A non-forced lockfile-only npm audit fix produced a zero-advisory candidate. The committed lockfile matches the reviewed candidate artifact byte-for-byte (Git blob `ab85231d2929e83c2e9b1a0f8ead594a2fef09bf`); the direct package manifest and production dependency entries are unchanged.

| Package | Prior | Reviewed |
| --- | --- | --- |
| ESLint | 10.11.0 | 10.15.0 |
| typescript-eslint | 8.71.0 | 8.74.0 |
| Vite | 8.3.2 | 8.3.8 |
| minimatch (transitive) | 10.2.6 | 11.0.9 |
| Zod (transitive) | 4.6.5 | 4.6.7 |

The update changes 39 existing development-only lockfile entries and introduces eight transitive development-only entries required by the updated build toolchain. The additional entries retain their registry-provided integrity hashes and license metadata (MIT, BlueOak-1.0.0 and 0BSD); several are optional platform-specific WASM build dependencies. No new direct application dependency or runtime UI asset is added. The [follow-up CI audit](https://github.com/AI-CJ/primary-care-emr/actions/runs/45561485342/job/139025991367) independently reported zero full and zero production npm advisories. The reusable dependency job archives both reports and blocks release checks when advisories are unresolved. This is a point-in-time registry audit, not a comprehensive assessment of the packaged Python runtime, backend dependencies or unknown vulnerabilities.

Accessibility changes add a keyboard bypass link, logical sign-in heading structure, accessible account descriptions and form names, focus restoration after account and portal-preview transitions, and a stable sign-in status region. The new Chromium script inspects the actual accessibility tree, named controls and landmarks, keyboard navigation, hidden draft fields, computed solid-surface contrast and responsive reflow. The first run exposed a test implementation defect: the flat CDP node array was not in depth-first reading order. The corrected check follows child IDs through ignored containers. The original browser clinical and reset checks passed on that run; the revised accessibility and deployment-verifier tests require their own passing run.

The deployment workflow writes an exact revision marker, restricts automatic releases to successful main checks and exercises the published fictional staff and patient workflows. The verifier is also exercised against the disposable local build before release. A successful GitHub deployment alone is distinct from successful external retrieval and application verification.

The [manual verification protocol](USABILITY_TEST_PROTOCOL.md) records environment coverage, screen-reader tasks, ten formative staff/patient scenarios and an anonymous observation sheet. No representative-user sessions, actual screen-reader speech checks, or participant results have been fabricated. Those manual activities remain open, as do comprehensive accessibility and security validation.

## Visual review and startup baseline (November 25, 2026)

[PR 82](https://github.com/AI-CJ/primary-care-emr/pull/82), head `ac5a68e`, passed all six [Checks jobs](https://github.com/AI-CJ/primary-care-emr/actions/runs/45564212912). The downloaded [rendered screenshot artifact](https://github.com/AI-CJ/primary-care-emr/actions/runs/45564212912/artifacts/14999093200) was inspected across ten images: staff and patient sign-in, dashboard, directory, chart summary, coded health record, patient home/settings and two mobile views (1280 and 360 CSS px). No release-blocking clipping or overlap was visible in these captures. The mobile chart is 3250 px tall; the notice takes considerable vertical space, and the record could benefit from more compact mobile navigation. These are next-pass usability findings, not user-test results. The reviewed PR merged at `af9ed7bae19dbef97e26a9c29eefbcd381ca48a0`; [main Checks](https://github.com/AI-CJ/primary-care-emr/actions/runs/45566625361) was still running at review time. No independent public-site screenshots were obtained.

### Startup baseline

The PR 82 [interactive browser log](https://github.com/AI-CJ/primary-care-emr/actions/runs/45564212912/job/139034932256) reports 18 pinned packages, 19.9 MiB of uncompressed on-disk runtime assets (up from the earlier 19.4 MiB before the catalog), 6.98 s fresh-tab workspace preparation and 0.39 s prepared sign-in. These are local CI observations, not public-network benchmarks. Source inspection shows Python core loading, package loading, backend archive fetch/unpack, Python imports, and synthetic database seeding on the initialization path. The catalog is packed into the archive but its checksum, parsing and search index are lazy, not invoked by the seed routine. Seeding generates four PBKDF2 account hashes; the unchanged production and browser work factor is 600,000 iterations.

The next performance increment overlaps the independent backend archive fetch with core/package initialization. A failed archive must prevent database initialization. Numeric worker stage timings distinguish core, packages, archive download, unpack, Python import, database seed, API import and wall-clock total; the overlapping stages are not additive. The build now reports sizes by asset group. Local browser and published-workspace smoke scripts log cold/prepared and same-worker timings as appropriate; request interception can disable browser cache, and the same-worker measurement is not a repeat-visit network benchmark. New focused tests cover concurrent startup and failure handling. No authentication work factor, seed data, diagnosis code, queue ordering or reset behavior is changed. Measure this candidate before considering further optimizations; the prior measurements alone do not establish a speedup.
