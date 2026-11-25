# Synthetic clinic population

The example clinic is seeded with 400 entirely fictional adult patients. The browser workspace preserves the three original reference identities and their established workflows, then adds 397 identities with generated longitudinal histories. Fresh local databases use the same population generator. An existing nonempty local database is not overwritten.

The generator uses a fixed pseudorandom seed and a supplied reference date; the same date and seed reproduce the same patient identities and relative history. It includes a mixture of preventive-care encounters, chronic conditions, resolved illnesses, combinations of comorbidities, dated vitals, medication indications, appointment histories, follow-up tasks, care goals, laboratory results and specialist referrals. Diagnosis codes use the pinned FY 2027 ICD-10-CM reference. The examples are authored fictional scenarios, not validated treatment guidelines, and the age/condition weights are not an epidemiological model.

The browser keeps its existing demo accounts instead of creating 400 logins. Clinicians can search all charts. Patient accounts retain the same patient-specific authorization boundaries. The directory renders 25 rows per page and searches the full list. Population initialization is measured separately from runtime and reference-account setup.

## Verification

The population tests assert record counts, age coverage, unique names, documented history, diagnosis diversity, same-patient associations, valid chronology, unique appointment slots and code titles against the pinned reference when present. Browser tests check the complete directory count, paging, search and reset. Use CI output for actual performance and test results; no measurements are assumed here.

No real patient identifiers, contact information or clinical records were used. The generated dataset must never be used for patient care or as a representative clinical research population.

## Longitudinal chart depth

Every generated chart receives a dated historical background with medical and surgical history, family history (including incomplete information), social circumstances and care preferences. The generator includes 23 authored diagnosis scenarios, condition-linked medication history, discontinued regimens, varied visit narratives and prior lab results. It preserves the fixed reference accounts and the original generated identities. Patients without active chronic disease remain represented; not every patient needs a prescription, referral or imaging study.

Historical imaging reports contain the study, modality, performance and report dates, indication, findings, impression and provenance. They are included only with an authored clinical context, including prior injury, selected persistent musculoskeletal symptoms, osteoporosis assessment or prior investigation of liver enzyme abnormalities. The reports are fictional text, not diagnostic image files, DICOM/PACS integration, orders, or recommendations. The staff health record shows the background; the labs/referrals section shows historical imaging. Patient sign-in and staff portal preview expose only reports explicitly shared for that patient. An empty report list does not assert that imaging has never occurred.

Clinical context references used in designing the fictional scenarios: [ACR Chronic Knee Pain](https://acsearch.acr.org/docs/69432/Narrative/), [ACR Low Back Pain](https://acsearch.acr.org/docs/69483/Narrative/), and [ACR Osteoporosis and Bone Mineral Density](https://acsearch.acr.org/docs/69358/Narrative/). These references informed scenario selection, not a validated clinical decision-support engine.

The additional tables are introduced by an additive migration; existing nonempty local databases are not reseeded. Background records and historical reports are read-only in this increment. The browser's isolated seed generates the population on a fresh workspace and reset restores it.

Tests cover all 400 background records, heterogeneous histories, imaging dates and study reasons, absence of contradictory diabetes/prediabetes labels, medication history, access control and patient-only report visibility. Browser checks exercise the existing reference chart's prior resolved wrist injury and its shared report. Consult the CI output for actual results and initialization measurements.
