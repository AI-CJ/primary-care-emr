# ICD-10-CM reference

## Source and reproducibility

The staff workspace uses the United States ICD-10-CM FY 2027 diagnosis code descriptions, effective October 1, 2026 through September 30, 2027. The data is official public reference material, distinct from the application source code.

- [CDC/NCHS FY 2027 release directory](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2027/)
- [CDC/NCHS code descriptions archive](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2027/icd10cm-code-descriptions-2027.zip)
- [CMS code descriptions and tabular order archive](https://www.cms.gov/files/zip/2027-code-descriptions-tabular-order.zip)

Reviewed CDC archive SHA-256: `93e3ad6004badf470c55bfe679b748ae88fd9b2b421851e409eec382c7713b9a`.

Generated catalog: 74,879 reportable codes, sorted by undotted code, with tab-delimited long descriptions and LF line endings. SHA-256: `623c7f250b800aa44e5c34efd7c37f168ceb2c41f33a8de11f9a9b4b6115e353`.

From the repository root run:

```sh
python -m scripts.prepare_icd10_catalog
```

Use `--archive /path/to/official-release.zip` for a previously downloaded archive, or `--force` to rebuild. Both import and loading reject a catalog that differs from the reviewed digest. The browser build includes the reference in its local runtime package; the ordinary API reads the same generated file. Nothing is sent to an outside diagnosis service when searching. Search uses official descriptions and code prefixes, includes newer alphanumeric categories, and returns up to 20 results per request. This is not a complete synonym index or clinical coding decision support system.

A future release update requires reviewing the official files, release/effective dates, code changes, importer, checksums, and regression tests together. Existing recorded codes retain their original release.

## Recording and reviewing

In the staff health record, choose a diagnosis from the search results, or explicitly record an uncoded problem. The reference provides candidate codes, not a diagnosis. In medication and laboratory request forms, select documented chart problems as indications. More than one problem can be selected; records without a confirmed indication display that fact. Never infer an indication from a medication or test name. A diagnosis code describes a condition or reason for care, not a drug or laboratory procedure identifier.

The PostgreSQL migration adds nullable coding fields, association tables and visit snapshots without rewriting older records. The browser uses the same ORM mappings in its isolated SQLite database. Staff views include codes and associated problems; the patient portal retains its plain-language projection. Finalized visits retain the snapshots recorded at the time of linking. The application does not validate all coding conventions, medical necessity, billing requirements, or clinical appropriateness. All chart data is fictional.
