# Synthetic clinic population

The example clinic is seeded with 400 entirely fictional adult patients. The browser workspace preserves the three original reference identities and their established workflows, then adds 397 identities with generated longitudinal histories. Fresh local databases use the same population generator. An existing nonempty local database is not overwritten.

The generator uses a fixed pseudorandom seed and a supplied reference date; the same date and seed reproduce the same patient identities and relative history. It includes a mixture of preventive-care encounters, chronic conditions, resolved illnesses, combinations of comorbidities, dated vitals, medication indications, appointment histories, follow-up tasks, care goals, laboratory results and specialist referrals. Diagnosis codes use the pinned FY 2027 ICD-10-CM reference. The examples are authored fictional scenarios, not validated treatment guidelines, and the age/condition weights are not an epidemiological model.

The browser keeps its existing demo accounts instead of creating 400 logins. Clinicians can search all charts. Patient accounts retain the same patient-specific authorization boundaries. The directory renders 25 rows per page and searches the full list. Population initialization is measured separately from runtime and reference-account setup.

## Verification

The population tests assert record counts, age coverage, unique names, documented history, diagnosis diversity, same-patient associations, valid chronology, unique appointment slots and code titles against the pinned reference when present. Browser tests check the complete directory count, paging, search and reset. Use CI output for actual performance and test results; no measurements are assumed here.

No real patient identifiers, contact information or clinical records were used. The generated dataset must never be used for patient care or as a representative clinical research population.
