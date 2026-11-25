# Interface review — November 25, 2026

## Reviewed evidence

Reviewed [PR 86](https://github.com/AI-CJ/primary-care-emr/pull/86) at `c79bf7dbdce5877389877aa3b8a8d3dd5a5b41a0`, with the pending-lab fix from [PR 87](https://github.com/AI-CJ/primary-care-emr/pull/87) integrated. All six jobs in [Checks 45574252700](https://github.com/AI-CJ/primary-care-emr/actions/runs/45574252700) passed. The backend job ran 392 tests; the interactive browser job passed clinical workflows, tab isolation, reset, accessibility-tree checks, keyboard transitions, sampled contrast, reflow, and the local published-workspace verifier. The actual [13-image Chromium artifact](https://github.com/AI-CJ/primary-care-emr/actions/runs/45574252700/artifacts/15003751064) was downloaded and visually inspected at both full-page overview and cropped detail scales. It covers the following synthetic-data states:

| Capture | Width × full-page height (CSS px) |
| --- | --- |
| Staff sign-in | 1280 × 900 |
| Staff dashboard | 1280 × 910 |
| Chart summary | 1280 × 1680 |
| Patient sign-in | 1280 × 900 |
| Patient home | 1280 × 1017 |
| Mobile patient home | 360 × 1814 |
| Mobile staff chart | 360 × 3250 |
| Coded health record | 1280 × 3148 |
| Directory | 1280 × 2095 |
| Patient settings | 1280 × 1045 |
| Labs/referrals/prior imaging | 1280 × 2250 |
| Immunizations | 1280 × 2180 |
| Pending labs after cancellation | 1280 × 4801 |

The captures show a consistent gunmetal staff identity and a softer emerald/aquamarine patient identity. The medication, diagnosis and vaccination histories and the recorded cancellation remain visible. No obvious release-blocking overlap was seen in the inspected states. The new pending-lab list consumes disproportionate vertical space (17 requests in the captured 4801 px page), with a mostly empty right column and a separate full-width action row for every request. The narrow chart and portal remain scroll-heavy; the educational-use notice is prominent and is retained. The two mobile captures are not a substitute for screenshots of every staff or portal destination; automated reflow and keyboard checks supplement but do not replace visual review or representative-user testing.

## Changes in this increment

- Place the lab resolution controls alongside the patient link on wider screens, with a full-width inline form only for the active request. Narrow screens stack the order details, patient link and controls in document order.
- Maintain 44 CSS px minimum targets, explicit patient/request context, all clinical indications and cancellation reasons, and existing authorization, result-recording, release, and audit semantics.
- Extend the browser smoke test with desktop geometry, 360 and 320 px reflow, touch targets, focus on the cancellation input and return focus after dismissal. Capture the narrow cancellation form for review. Existing cancellation, persistence, and result-release checks remain in the suite.

These changes are derived from the inspected rendered artifact; the candidate must pass its own CI and its new captures must be inspected before describing the layout as verified. There is no new dependency or clinical API/schema change.

## Performance and release state

The PR 86 [interactive browser log](https://github.com/AI-CJ/primary-care-emr/actions/runs/45574252700/job/139068128040) recorded 9.05 s fresh-tab preparation, 0.90 s prepared staff sign-in, and 0.89 s same-worker patient sign-in, on the local CI server. Its startup instrumentation recorded 8,437 ms total (archive download 22 ms, core 1,672 ms, packages 556 ms, unpack 38 ms, Python import 2,879 ms, database seed 1,708 ms, including population seed 1,100 ms, and API import 484 ms). Stages overlap or are nested; they are not additive. These timings are not public-network measurements.

PR 82 was already merged after the prior visual review; PR 83–85 and PR 87 were also merged. PR 86 was merged after confirming its six green jobs and inspecting its screenshot artifact, at main revision `375460a83937124edb6c61be8f82dccbc6279a59`. Main checks and exact Pages revision require separate confirmation. PR 88's performance branch was green on its own base when checked, but was not merged by this interface increment because it must be reconciled with the new main, including shared seed code and audit documentation. The independent network environment could not resolve GitHub for a local clone, and retrieval of the public site and release.json was unsuccessful. No independent live-site inspection or current published revision is claimed.

Next: verify the compact worklist candidate and inspect both new captures; reconcile PR 88 with current main, perform the integrated clinical, security, provenance and deployment audit; incorporate exact final CI/deployment evidence and measurements into UX_AUDIT.md and then the README. Screen-reader speech, representative-user testing, actual browser zoom and independent public-network performance remain unverified.
