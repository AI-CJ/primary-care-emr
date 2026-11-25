# Clinical integrity and dependency review — November 25, 2026

## Verified baseline

Reviewed main revision [375460a83937124edb6c61be8f82dccbc6279a59](https://github.com/AI-CJ/primary-care-emr/commit/375460a83937124edb6c61be8f82dccbc6279a59), following the verified merges of PRs 82–87. [Main Checks 45584666419](https://github.com/AI-CJ/primary-care-emr/actions/runs/45584666419) completed successfully (six jobs, 392 backend tests and 37 frontend tests). [Pages run 45585129869](https://github.com/AI-CJ/primary-care-emr/actions/runs/45585129869/job/139104664177) verified the exact release marker and public clinician/patient access, shared result, preferences and reset. The deployment's log is external browser verification from CI, not an independent manual visit from this review environment.

The existing [rendered captures](https://github.com/AI-CJ/primary-care-emr/actions/runs/45584666419/artifacts/15007572843) are available, but were not visually inspected during this session. PR 88 (startup optimization) and PR 89 (compact pending lab interface) are independent active branches; this audit does not edit their files.

## Clinical source inspection and regression coverage

- The FY2027 ICD-10-CM catalog importer/loader uses a reviewed source digest, a generated digest and a reportable-code count of 74,879. The catalog is a reference, not a clinical coding or appropriateness validator.
- Staff-only search and chart writes are mediated by authentication middleware, patient-only projections use authenticated patient identity, and lookup terms use POST rather than URL query parameters. Problem selections are patient-scoped and retained historical snapshots are not rewritten on a subsequent problem edit. Existing regression tests check cross-chart indication rejection, finalized visit snapshots and patient portal projection. The new test extends explicit front-desk and patient denial coverage to all terminology search endpoints and vaccination writes, while confirming clinician access.
- The synthetic population's condition, medication and test associations are explicitly authored scenarios, not newly inferred indications. Existing tests verify ownership, recorded ICD-10 codes and chronological seed constraints. The medication/vaccine importer selects official vocabulary entries and the synthetic vaccine dates are checked against birth and the seed date.
- A source inspection found that changing a patient's birth date could make a previously recorded vaccination precede birth even though the vaccination creation endpoint prohibits that state. This candidate checks active vaccination records under the existing patient lock before a birth date change, rejects conflicts without changing demographics, and permits a reconciled date after an erroneous vaccination is explicitly corrected. It preserves the voided record. A regression exercises conflict, unchanged date after rejection, unrelated demographic edit and correction. This is a narrow vaccination chronology invariant, not a comprehensive clinical timeline validator.

## Terminology provenance and runtime evidence

[Backend job 139103101879](https://github.com/AI-CJ/primary-care-emr/actions/runs/45584666419/job/139103101879) and [browser job 139103101967](https://github.com/AI-CJ/primary-care-emr/actions/runs/45584666419/job/139103101967) recorded the same source digests and counts. See [ICD-10 source evidence](https://github.com/AI-CJ/primary-care-emr/actions/runs/45584666419/artifacts/15007443684) and [CDC terminology source evidence](https://github.com/AI-CJ/primary-care-emr/actions/runs/45584666419/artifacts/15008022037).

| Reference | Imported records | Source SHA-256 |
| --- | ---: | --- |
| RxNorm | 34,034 | `c742a6c4b2995194aa3479400e08a7c1ad707178bfc80fe9c8cd7afa693ae987` |
| CVX | 245 | `efd2a6770f0f648ce76e10ac2889602b2ea8fa8ca4b63deb33ca883e7d0d7413` |
| MVX | 89 | `4c0c145b4609d0c687e51987effbe808af4e55b7dcebdaf947660d3915600ed8` |

The existing code/reference docs retain attribution to CDC/NCHS, CMS and NLM. No license, copyright notice, repository visibility or source vocabulary is changed by this audit. A complete third-party license/notice inventory, visual asset usage review and independent source comparison remain open.

Measured runtime from the successful browser job: core 13,530,536 bytes; package assets 6,753,541 bytes; backend archive 643,486 bytes; deferred terminology archives 472,206 bytes. Total on-disk runtime 20.4 MiB including deferred assets; this is not measured network transfer. Fresh-tab preparation 12.07 s, prepared sign-in 0.91 s, warm same-worker patient sign-in 0.93 s, fresh-context navigation through sign-in 12.05 s (local CI). Public Pages workflow measured 8.29 s preparation and 0.38 s prepared clinician sign-in. These observations are not controlled before/after or throttled-network benchmarks; PR 88 is investigating the startup path separately.

## Python advisory gate

The baseline npm audit reported zero advisories in both full and production trees. A Python advisory scan had not been part of the release gate. This candidate adds an isolated, pinned pip-audit scanner to the reusable dependency-review workflow. The job installs and checks the backend environment, freezes resolved distributions, resolves the same package closure from the versioned Pyodide lock and archives the exact inventories and machine-readable advisory reports. Non-wheel runtime modules are inventoried separately, not silently treated as audited PyPI packages. Missing reports, skipped wheel distributions, coverage/version mismatches and unresolved advisories fail the gate. Tests exercise transitive inventory resolution and rejection of incomplete or vulnerable reports. No speculative production dependency upgrade or advisory exemption is included. The scanner must pass in CI before merging; the actual first audit results are not yet known.

This is an advisory database review, not verification of all native libraries, CPython/WASM core, the security of the build supply chain, formal penetration testing, human clinical validation or certification. No real patient information is involved.

## Next release gates

Review the candidate's exact CI results and advisory inventory, resolve any actual vulnerabilities using compatible pinned remediation, and only merge when all checks pass. Integrate the active startup and worklist PRs without losing either feature. Re-run full main and Pages verification, inspect actual integrated desktop/mobile captures, complete provenance and accessibility checks, document startup timing with comparable test conditions, and reconcile the final release audit and README against the deployed revision.
