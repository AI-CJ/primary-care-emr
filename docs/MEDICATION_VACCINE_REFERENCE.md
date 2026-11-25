# Medication and immunization reference catalogs

## Sources and versioning

- National Library of Medicine, [RxNorm Current Prescribable Content](https://www.nlm.nih.gov/research/umls/rxnorm/docs/prescribe.html). The November 2, 2026 monthly unrestricted subset is pinned by archive filename and NLM's published MD5 checksum. The importer retains active normalized RxNorm ingredient, brand, clinical drug and package concepts (IN, PIN, MIN, BN, SCD, SBD, GPCK and BPCK) whose names fit the chart field. No proprietary UMLS source vocabularies are imported.
- CDC [CVX vaccine code set](https://www2.cdc.gov/vaccines/iis/iisstandards/vaccines.asp?rpt=cvx) and [MVX manufacturer code set](https://www2.cdc.gov/vaccines/iis/iisstandards/vaccines.asp?rpt=mvx). Import the official flat files, preserve leading zeros and code statuses, and retain inactive and non-US historical formulations. Pending, never-active and non-vaccine entries are not selectable in the vaccination form. The CDC files change over time; record their SHA-256 and retain the source files used for the verified browser build. The Pages workflow reuses those CDC source files from the successful main-branch checks run.

Generate reference files from the repository root:

```bash
python -m scripts.prepare_medication_vaccine_catalogs
```

The importer accepts explicit local source files via `--rxnorm`, `--cvx`, and `--mvx` for reproducibility. It reports concept counts, sizes and source digests. Downloaded source files and derived catalogs are excluded from Git. Build the browser runtime using the existing build script; separate compressed same-origin reference assets are loaded on first relevant search or coded write, not during login. Only a small exact seed terminology snapshot is included with the initial backend archive. The API-backed local seed requires the generated snapshot.

## Clinical workflow

RxNorm searches accept name or identifier. Staff explicitly choose a concept, and the server validates the supplied name against the selected code. Existing uncoded entries are retained, and the original terminology identifier and release are frozen in linked encounter snapshots. Existing coded names are not automatically recoded during an unrelated edit. Seeded medication ingredients are matched against the pinned official names, never by guessing a strength or brand.

Staff immunizations are a separate chart section. Each record includes a date, CVX identifier and name, source (clinic, historical record or patient-reported), optional MVX manufacturer, lot, dose number, route, site and notes. The API rejects future dates, dates before birth, current-clinic use of inactive codes, and duplicate active patient/date/code records. Corrections retain original records and require a reason; the patient portal excludes voided records and returns only records for the authenticated patient. Missing historical details remain unknown. Fictional charts have varied, incomplete historical vaccine records, including historically appropriate formulations and known manufacturers only when documented in the authored scenario.

## Limitations

These are clinical terminology and documentation features, not e-prescribing, drug interaction or allergy checking, dosing guidance, vaccine eligibility/forecasting, inventory, registry reporting, or a claim of complete vaccine schedule adherence. Product-level manufacturer compatibility is not verified by an MVX code alone. Never enter real patient information or rely on the system for clinical decisions. Existing nonempty local databases are not overwritten. Review official reference updates, provenance and regression results before changing the selected vocabulary releases.
