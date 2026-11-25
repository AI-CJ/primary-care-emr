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

The baseline npm audit reported zero advisories in both full and production trees. A Python advisory scan had not been part of the release gate. This candidate adds an isolated, pinned pip-audit scanner to the reusable dependency-review workflow. The job installs and checks the backend environment, freezes resolved distributions, resolves the same package closure from the versioned Pyodide lock and archives the exact inventories and machine-readable advisory reports. Non-wheel runtime modules are inventoried separately, not silently treated as audited PyPI packages. Missing reports, skipped wheel distributions, coverage/version mismatches and unresolved advisories fail the gate. Tests exercise transitive inventory resolution and rejection of incomplete or vulnerable reports. No advisory exemptions are included. The scanner must pass in CI before merging.

This is an advisory database review, not verification of all native libraries, CPython/WASM core, the security of the build supply chain, formal penetration testing, human clinical validation or certification. No real patient information is involved.

## Actual advisory findings and remediation

The first gate ran at 10:27 UTC on November 25, 2026. [Initial scan and log](https://github.com/AI-CJ/primary-care-emr/actions/runs/45595160829/job/139139179282) and [machine-readable inventory and reports](https://github.com/AI-CJ/primary-care-emr/actions/runs/45595160829/artifacts/15012144104) covered 29 server distributions and 18 browser distributions without coverage errors. The gate rejected 13 advisory matches:

| Environment | Package | Initial version | Advisories | Reported fixed version covering the listed findings |
| --- | --- | --- | --- | --- |
| Server | opentelemetry-api | 1.45.0 | GHSA-xcq7-p3pf-p88h, GHSA-mf5v-w3w3-f6cg | 1.45.2 |
| Browser | anyio | 4.13.0 | PYSEC-2026-4025, PYSEC-2026-4024 | 4.14.2 |
| Browser | cryptography | 47.0.0 | PYSEC-2026-3552, PYSEC-2026-3553, PYSEC-2026-3554, GHSA-537c-gmf6-5ccf | 50.0.0 |
| Browser | starlette | 1.0.0 | PYSEC-2026-161, PYSEC-2026-249, PYSEC-2026-248, PYSEC-2026-2281, PYSEC-2026-2280 | 1.3.1 |

The server pin was corrected in [f427594](https://github.com/AI-CJ/primary-care-emr/commit/f427594a26e28a79fe1a8f5034428c16c8d433c1). At 10:29 UTC the [repeat scan](https://github.com/AI-CJ/primary-care-emr/actions/runs/45595408174/job/139140044895) verified zero known advisory or coverage findings for all 29 server distributions. It independently reproduced all 11 browser findings. See the [second inventory and reports](https://github.com/AI-CJ/primary-care-emr/actions/runs/45595408174/artifacts/15013530322). The gate remains failing deliberately; PR 90 is not release-ready. Advisory matches identify affected published package versions; applicability to reachable browser code paths has not been established.

The stable Pyodide 314.0.8 runtime lock still selects the affected browser versions. Upstream release and package-file review did not establish a compatible patched cryptography Emscripten wheel. Native Linux wheels are not a browser-compatible fix. The pure-Python AnyIO and Starlette fixes also need actual FastAPI dependency-constraint and browser compatibility verification; do not alter the audit inventory without changing the artifacts actually built. Prefer a verified upstream runtime upgrade or a shared, digest-pinned effective runtime lock. For cryptography, coordinate with PR 88, which already modifies the browser password path, to evaluate an appropriately reviewed native Web Crypto implementation or compatible patched wheel. Preserve PBKDF2 parameters, server password format, authentication and reset/isolation behavior; do not substitute a weaker hash or silently exclude an affected package.

The initial backend regression job [139139179079](https://github.com/AI-CJ/primary-care-emr/actions/runs/45595160829/job/139139179079), frontend build and API/browser smoke passed before the server pin change. Those are not final candidate checks. Re-run every job for the integrated candidate.

A visual asset inspection also identified the default Vite favicon referenced by frontend/index.html and several starter-template assets. The favicon still needs replacement with original project artwork; unused-asset status and required notices must be checked before removal. Do not infer licensing or authorship from the filenames or from a public repository without an explicit license.

## Next release gates

Resolve the remaining browser advisories using compatible pinned remediation and merge only after all checks pass. PRs 88 and 89 passed their earlier six-job checks, but those checks did not include the newly discovered Python findings; do not treat those older green checks as a complete release security gate. Integrate the active startup and worklist PRs without losing either feature. Re-run full main and Pages verification, inspect actual integrated desktop/mobile captures, complete provenance and accessibility checks, document startup timing with comparable test conditions, and reconcile the final release audit and README against the deployed revision.

## Verified remediation and release

The preceding failed scans and pending gates are retained as historical evidence. PR 90 subsequently resolved the listed advisory findings and merged at `1b68e37f8ed2adf144f4f7d67b10683656730688`. The browser build uses digest-pinned pure-Python dependency updates and removes the affected browser cryptography wheel; browser password verification uses the native PBKDF2 path without reducing the existing work factor. The effective packaged runtime inventory and installed server inventory are audited, rather than the obsolete upstream wheel set.

[Main checks 45618206243](https://github.com/AI-CJ/primary-care-emr/actions/runs/45618206243) passed all seven jobs, including 400 backend and 41 frontend tests. The [Python gate](https://github.com/AI-CJ/primary-care-emr/actions/runs/45618206243/job/139219037628) found zero advisory or coverage findings across 29 server distributions and 15 browser distributions. The [npm gate](https://github.com/AI-CJ/primary-care-emr/actions/runs/45618206243/job/139219037697) found zero advisories in both trees. [Archived Python evidence](https://github.com/AI-CJ/primary-care-emr/actions/runs/45618206243/artifacts/15023032182) records the reviewed inventories. The [published verification](https://github.com/AI-CJ/primary-care-emr/actions/runs/45618722375/job/139220861241) matched the application SHA before and after the live smoke and checked the distributed third-party notices.

The final application audit, measured startup profiles and rendered review appear in [UX_AUDIT.md](UX_AUDIT.md). This closes the identified release advisory gate; it is not a guarantee against undisclosed vulnerabilities, an independent penetration test, an exhaustive supply-chain or license review, or clinical/security certification.
