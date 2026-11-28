# Speed, usability and accessibility review

Date: November 28, 2026

Baseline: [`ef2a0a1`](https://github.com/AI-CJ/primary-care-emr/commit/ef2a0a149e4bd1890efe4cb4452e94ec1e138385). Reviewed application: [`c318f93`](https://github.com/AI-CJ/primary-care-emr/commit/c318f934b459862b4639769d72376634738733c6). Integration: [PR 93](https://github.com/AI-CJ/primary-care-emr/pull/93).

## Scope and decisions

The review targeted unnecessary startup downloads, dashboard work, long care queues, and keyboard navigation failures. It preserves the clinical route logic, authorization, record lifecycle, existing password parameters, tab isolation, synthetic population and reference provenance.

### Startup and dashboard

- Clinical screens load when opened. The first staff dashboard stays in the initial bundle, and selecting patient sign-in prepares the patient portal's code while credentials are entered. This avoids making the first workspace wait for another screen download.
- A failed screen download leaves the session and staff navigation available. Its error heading receives focus. Reloading requires confirmation because it resets the public tab's data.
- The full diagnosis catalog is excluded from the startup backend archive. Diagnosis searches and coded problem writes load the fixed same-origin `icd10.zip`; subsequent lookups reuse it. Failed downloads/unpacking can be retried. Search text and patient identifiers are never included in asset URLs.
- `GET /worklists/counts` replaces six complete worklist responses on the dashboard. One SQL statement computes six counts without loading chart objects. The endpoint retains staff-only authorization, no-store responses, archive filtering, pending/active status and finalized-result release rules. Counts are not cached. Appointment-request totals are exact even above the list endpoint's 100-record page.

The first candidate also deferred the dashboard. In the controlled test that increased prepared sign-in from 0.163 seconds to 0.897 seconds. Keeping that small first screen ready reduced the final measured sign-in to 0.158 seconds while retaining the larger screen splits. The additional readiness commit records this measured correction.

### Worklist usability

Open Follow-ups, Active Care Goals and Pending Referrals now search the entire returned queue before displaying six records per page. The server's priority/date ordering is retained. Search and page choice survive refresh; shortened queues clamp to a valid page. Clearing search returns focus to its input, and paging focuses the updated result summary during the React commit. This avoids a delayed animation-frame callback stealing focus from subsequent typing.

The browser fixture contained 44 open follow-ups, 77 active goals and 40 pending referrals. Each showed six records initially; every record remained reachable. Tests searched for a record on the second page, refreshed while filtered, cleared empty results, opened the filtered chart and checked 320px layout and 44px controls. Search, result counts and pagination have explicit accessible names. Existing pending-lab filtering/pagination remains in place.

### Keyboard, motion and contrast

A shared inline-editor hook transfers focus into new editors, restores the exact initiating control on cancellation and focuses a stable card heading after saving. Persistent atomic status regions announce saved state without a delayed focus jump after a reload. Record-specific Edit names distinguish repeated actions. These changes cover problems, medications, allergies, vitals, immunizations, appointment add/reschedule, visit-note editing and chart archive/reactivation. Destructive chart confirmation initially focuses Cancel.

The clinical reference picker consumes Enter while suggestions are open but none is active, preventing accidental form submission. It does not silently choose a code; dismissing suggestions still permits intentional uncoded entry. Routed appointment/note scrolling honors reduced-motion preferences. Staff navigation retains a visible selected boundary under forced colors.

## Measurements

The same final `scripts/profile_browser_startup.py` measured both built revisions sequentially on one machine. Its HTTP origin applies a shared 20 Mbit/s body-transfer budget and a 40 ms delay per request. Cold and cached-repeat visits use one browser context; the repeat starts a new worker and database. This is a controlled local observation, not a public-network or low-end-device benchmark.

| Size or work metric | Baseline | Optimized |
| --- | ---: | ---: |
| Initial JavaScript entry, minified bytes | 501,446 | 261,679 |
| Same entry compressed with Python gzip, bytes | 122,126 | 80,077 |
| Startup backend archive, bytes | 644,852 | 79,599 |
| Dashboard queue API requests | 6 | 1 |
| Queue response bodies, UTF-8 bytes | 73,417 | 78 |
| Cold origin body bytes through dashboard counts | 19,208,189 | 18,397,055 |
| Cached-repeat origin body bytes | 9,605,141 | 9,605,751 |

The initial entry is 47.8% smaller before compression and 34.4% smaller with this gzip procedure. The backend archive is 87.7% smaller; queue response bodies are 99.9% smaller. The full runtime distribution remains about 18.2 MiB because the reference data is deferred, not removed. Deferred terminology archives total 1,038,479 bytes. Worker messages are measured using counters and lengths; the profiler does not store credentials or clinical response bodies.

| Observed timing | Baseline cold | Optimized cold | Baseline cached repeat | Optimized cached repeat |
| --- | ---: | ---: | ---: | ---: |
| Sign-in shell visible | 0.443 s | 0.314 s | 0.118 s | 0.102 s |
| Workspace ready | 15.401 s | 15.219 s | 12.090 s | 12.018 s |
| Prepared sign-in, heading visible | 0.163 s | 0.158 s | 0.384 s | 0.381 s |
| Sign-in through all dashboard queue counts | 0.534 s | 0.269 s | 0.388 s | 0.385 s |

These are individual observations, not a statistical performance claim. The reduction in transferred code and queue work is substantial, but full cold workspace readiness changed little. Python core/package initialization and imports remain the dominant costs, and readiness still exceeds the five-second stretch target. No material cold-start speedup is claimed.

## Validation evidence

The following checks passed locally before integration:

| Check | Result |
| --- | --- |
| Backend suite | 405 tests passed |
| Frontend suite | 48 tests passed |
| ESLint, TypeScript and production build | Passed |
| Packaged clinical API | Coded diagnosis create/update and invalid-code handling, linked records, notes, lab release, referrals, care and portal requests passed |
| Full interactive browser | Staff/patient workflows, mutations, separate contexts, preferences and reset passed |
| Deferred-screen regression | Unused clinical chunks absent initially, heading focus after reveal, failed-tile recovery without sign-out and patient sign-in passed |
| Worklist regressions | Full-data search, six-row paging, ordering, focus, refresh, clear/no matches and chart access passed for all three queues |
| Accessibility regression | Editor focus/cancel/save, contextual labels, reference Enter, reduced motion, forced colors, named controls, one main landmark and seven portal sections at 768/360/320px passed |
| Startup failure handling | Failed archive, reset recovery, invalid credentials, valid sign-in and cached repeat passed |

The accessibility checks inspect Chromium's accessibility tree and actual focus, not only markup. Sampled text contrast was 6.85:1, 7.54:1 and 9.70:1; sampled field boundaries were 3.50:1. Desktop and mobile application captures, including a 320px six-row follow-up queue, a 360px medication editor, forced-colors navigation and archive confirmation were visually reviewed. No clipping or overlap was observed in those sampled states. The shared application assets matched the accessibility test build byte-for-byte before the small first-screen readiness adjustment; that adjustment received a fresh screen-loading and startup regression.

PostgreSQL migration/API-backed browser checks and dependency inventories remain required in GitHub CI. [PR checks](https://github.com/AI-CJ/primary-care-emr/pull/93/checks), [main Checks](https://github.com/AI-CJ/primary-care-emr/actions/workflows/checks.yml) and [Pages deployment](https://github.com/AI-CJ/primary-care-emr/actions/workflows/pages.yml) provide integration and publication evidence for their exact revisions. This local review does not substitute for those gates.

## Reproduce the comparison

Build both revisions with their existing runtime preparation and frontend build instructions. Keep each `frontend/dist` in a separate checkout. Run the final profiler against each build from the optimized checkout:

```bash
backend/.venv/bin/python scripts/profile_browser_startup.py --dist /path/to/baseline/frontend/dist
backend/.venv/bin/python scripts/profile_browser_startup.py --dist /path/to/optimized/frontend/dist
```

The interactive CI job runs the new worklist/screen-loading checks through `check_browser_emr.py` and the keyboard checks through `check_accessibility.py`. Its `emr-workspace-screenshots` artifact records rendered application captures.

## Limits and references

This remains a synthetic educational application. Manual screen-reader speech testing, representative-user usability sessions, comprehensive WCAG conformance and clinical/security certification are not established. Some chart and interactive queue screens still require substantial scrolling. This pass bounds three additional queues; it does not claim every possible workflow is optimized.

Design references:

- [React lazy loading](https://react.dev/reference/react/lazy) and [Suspense reveal behavior](https://react.dev/reference/react/Suspense).
- [W3C focus order](https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html).
- [W3C status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html).
