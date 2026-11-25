# Primary Care EMR

[![Checks](https://github.com/AI-CJ/primary-care-emr/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/AI-CJ/primary-care-emr/actions/workflows/checks.yml)

Primary Care EMR is a full-stack electronic medical record and patient portal for a fictional outpatient practice. The application brings scheduling, longitudinal patient charts, visit documentation, clinical orders, immunizations and care coordination together in one workspace.

**[Open the live EMR](https://ai-cj.github.io/primary-care-emr/)** · [Design rationale](docs/UX_DESIGN.md) · [Release audit](docs/UX_AUDIT.md)

> Educational portfolio project. All patient records are fictional. Do not enter real patient information or personal credentials. Neither the public nor local application is approved for clinical use.

## Explore the application

| Role | Available workflows |
| --- | --- |
| Administrator | Clinical workspace, chart archive/reactivation, audit review and CSV export |
| Clinician | Schedule, searchable patient charts, clinical documentation, medication and vaccine records, orders and care coordination |
| Patient | Own health record, vaccinations, appointments, shared test and imaging reports, care goals and communication preferences |

Select a staff account on the sign-in screen, or choose **Switch to patient sign-in** to explore the portal as Jordan Lee or Maria Thompson. The application prepares its isolated Python runtime while the sign-in page is open. Once **Workspace ready** appears, account sign-in typically takes a fraction of a second in the measured test environments.

Changes persist in the current tab when switching accounts. **Demo reset**, refreshing, or closing the tab restores or discards the local workspace. No orders, messages or referrals are transmitted to outside clinical services.

## Clinical workspace

- Dashboard with today's schedule and live work-queue counts.
- 400 searchable fictional adult patient charts; the directory renders 25 records per page.
- Dated medical, surgical, family and social history, personal care context, active and historical diagnoses, medication regimens, allergies and serial vital signs.
- ICD-10-CM diagnosis selection and explicitly documented medication and laboratory indications.
- RxNorm medication lookup, optional standardized medication identifiers and historical encounter snapshots.
- Immunization history with CVX vaccine and MVX manufacturer selection, administration dates, dose, lot, route, site, source and retained corrections.
- Appointment scheduling, conflict checks, rescheduling, check-in, completion, cancellation and no-show tracking.
- Structured visit notes, draft review, finalization, linked clinical snapshots, append-only addenda and patient instructions.
- Pending laboratory worklist and chart-level result recording or cancellation with a reason; completed results enter a separate release workflow.
- Prior imaging report history with indication, findings, impression and report dates; referrals, care goals and follow-up tasks.
- Administrator-only archive/reactivation and audit review, retaining clinical history.

The seed includes healthy patients and patients with multiple chronic conditions, resolved illnesses, past procedures, medication changes, differing social circumstances and incomplete historical documentation. It is reproducible for a given reference date and seed, not a clinically validated or epidemiologically representative population. See [synthetic population design](docs/SYNTHETIC_POPULATION.md).

### Patient portal

The patient experience uses a lighter visual treatment and plain-language navigation. Home emphasizes the next appointment and common tasks. Patients can review their own recorded conditions, medications, allergies, vital signs, vaccinations, appointments, visits, released lab results, shared historical imaging reports, referrals and care goals. They can request appointment changes and save communication preferences. Clinical records are read-only from patient accounts; appointment requests require staff action. Staff have a chart-scoped read-only portal preview.

### Reference terminology

| Vocabulary | Source | Verified release count |
| --- | --- | ---: |
| ICD-10-CM | CDC/NCHS, FY 2027 | 74,879 reportable codes |
| RxNorm | NLM Current Prescribable Content, November 2, 2026 | 34,034 concepts |
| CVX | CDC vaccine vocabulary | 245 included entries |
| MVX | CDC manufacturer vocabulary | 89 entries |

Reference imports record source provenance and version identifiers. The medication and vaccine catalogs load on demand from same-origin assets, not by sending patient searches to external services. Clinical selections and historical snapshots retain recorded identifiers; missing information is not inferred. See [ICD-10-CM](docs/ICD10_REFERENCE.md) and [medication/vaccine references](docs/MEDICATION_VACCINE_REFERENCE.md) for import scope and limitations.

## Design and accessibility

The clinical and patient interfaces use a shared gunmetal, emerald and sea-glass palette with restrained terracotta accents and original inline SVG brand artwork. The clinical workspace favors efficient navigation and information density; the patient portal favors readability and explicit task labels. Responsive controls, keyboard focus, accessibility-tree checks, sampled contrast and narrow-screen reflow are part of verification. See the [design rationale](docs/UX_DESIGN.md) and [release audit](docs/UX_AUDIT.md). Full accessibility conformance and representative-user validation have not been established.

## Architecture

The same React frontend and FastAPI routes support two execution modes.

```text
Local / API-backed application
  React + TypeScript ── HTTP / JSON ── FastAPI + Pydantic
                                         │ SQLAlchemy
                                         ▼
                                    PostgreSQL 17
                                    Alembic migrations

Public GitHub Pages application
  React + TypeScript ── worker messages ── Python / Pyodide
                                            │ FastAPI + SQLAlchemy
                                            ▼
                                       In-memory SQLite
                                       One database per tab
```

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, CSS |
| Clinical API | Python 3.12, FastAPI, Pydantic, SQLAlchemy |
| Local database | PostgreSQL 17, psycopg, Alembic |
| Public runtime | Pyodide 314.0.8, WebAssembly, Web Worker, SQLite |
| Delivery | Docker Compose, GitHub Actions, GitHub Pages |
| Verification | Python unittest, Node test runner, ESLint, TypeScript, Playwright/Chromium, npm audit, pip-audit |

The API-backed application enforces role restrictions and database transactions on the server. The public build exercises the same clinical route logic in an isolated browser worker and does not require a hosted database. Browser-local accounts are illustrative, not a security boundary against a user controlling their browser. SQLite uses ORM metadata and serialized requests rather than PostgreSQL's migration and concurrency guarantees.

## Run locally

Use Python 3.12, a supported Node.js 22 release, npm, Git, Docker and Docker Compose. Commands are written for a Linux or WSL shell.

### 1. Start the database

```bash
git clone https://github.com/AI-CJ/primary-care-emr.git
cd primary-care-emr
cp .env.example .env
```

Replace the example password in `.env` with a local-only value. The file is ignored by Git. Start PostgreSQL:

```bash
docker compose up -d
docker compose exec database sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### 2. Prepare the API and fictional data

From the repository root:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m scripts.prepare_icd10_catalog
python -m scripts.prepare_medication_vaccine_catalogs
alembic upgrade head
python -m backend.seed
python -m backend.bootstrap_staff --username demo.clinician --role clinician
python -m backend.bootstrap_staff --username demo.admin --role admin
python -m backend.bootstrap_patient --username demo.patient --patient-id 1
uvicorn backend.main:app --reload
```

The two preparation commands download and validate public reference files. Generated catalogs are not committed to Git. The medication/vaccine importer also prepares the small official seed-reference snapshot required for the full population. A fresh local database receives 400 fictional charts. The seeder skips an existing nonempty database; do not remove existing data merely to rerun it. Account setup prompts for passwords (12–128 characters). Confirm the patient's chart ID before linking a local account.

API: `http://127.0.0.1:8000` · OpenAPI: `http://127.0.0.1:8000/docs`.

### 3. Start the frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173` and sign in with a local account.

### Reproduce the public browser build

From the repository root:

```bash
python scripts/build_browser_runtime.py
cd frontend
npm ci
VITE_EMR_BROWSER=1 npm run build
npm run preview
```

The build script prepares the official references, pinned browser runtime and local distribution notices. Open the URL printed by Vite. No PostgreSQL service is needed. See the [frontend guide](frontend/README.md) and [workflow reference](docs/WORKFLOWS.md).

## Verification and release

The audited application revision [`1b68e37`](https://github.com/AI-CJ/primary-care-emr/commit/1b68e37f8ed2adf144f4f7d67b10683656730688) passed all seven main-branch CI jobs and was deployed and verified on November 25, 2026, at 7:59 AM Eastern. The evidence below refers to that application revision, not to a subsequent documentation-only commit.

| Check | Verified result |
| --- | --- |
| Backend tests | 400 passed |
| Frontend tests | 41 passed; lint and production build passed |
| PostgreSQL migration and API-backed browser workflow | Passed |
| Browser-only clinical API, interactive workflow, startup profile and accessibility checks | Passed |
| Historical static preview smoke | Passed |
| npm dependency audit | Zero reported advisories in full and production trees |
| Python dependency audit | Zero advisory or coverage findings across 29 server and 15 browser wheel distributions |
| GitHub Pages verification | Exact revision, distributed notices, 400-chart search, clinician/patient workflows, historical reports, lab cancellation, preferences and reset |

[Main Checks](https://github.com/AI-CJ/primary-care-emr/actions/runs/45618206243) · [Published verification](https://github.com/AI-CJ/primary-care-emr/actions/runs/45618722375) · [Engineering audit](docs/UX_AUDIT.md) · [Security review](docs/CLINICAL_SECURITY_REVIEW_2026-11-25.md)

### Run checks

Use a disposable test database and the Python environment prepared above.

```bash
# From the repository root
python -m unittest discover -s backend/tests -p 'test_*.py'

# Frontend
cd frontend
npm ci
npm run lint
npm test
npm run build
```

The [CI workflow](.github/workflows/checks.yml) contains the PostgreSQL configuration, migration checks, Chromium workflow and runtime profiling commands. To check a published revision from a network-enabled environment, install Playwright and Chromium, then run from the repository root:

```bash
python -m scripts.check_published_workspace --revision <full-commit-sha>
```

### Loading performance

Startup preparation starts before the user signs in. The runtime downloads its independent backend archive concurrently, derives the fixed demo account hashes without weakening the existing PBKDF2 parameters, and defers full medication and vaccine lookup assets until requested. The verified build contains 18.2 MiB of on-disk runtime assets, including approximately 461 KiB of deferred terminology archives.

| Measured procedure | Sign-in shell visible | Workspace ready | Prepared sign-in |
| --- | ---: | ---: | ---: |
| Local fresh-tab browser smoke | Not separately measured | 9.08 s | 0.40 s |
| Controlled cold profile | 0.410 s | 16.303 s | 0.383 s |
| Controlled cached-repeat profile | 0.127 s | 13.012 s | 0.378 s |
| Published Pages browser | Not separately measured | 10.24 s | 0.40 s |

Same-worker patient sign-in measured 0.17 s. The controlled profile uses a shared 20 Mbit/s local payload budget and a 40 ms delay per request; it observed 19,201,069 bytes served cold and 9,605,141 bytes on the cached repeat. These are measured observations from CI, not guaranteed timings or an assertion of a controlled speedup over the original release. Runtime initialization remains above the five-second stretch target. Network quality, CPU and browser cache behavior affect readiness. [Profile source](scripts/profile_browser_startup.py) · [Main measurements](https://github.com/AI-CJ/primary-care-emr/actions/runs/45618206243/job/139219037552)

## Reference screenshots

The [verified application screenshot archive](https://github.com/AI-CJ/primary-care-emr/actions/runs/45618206243/artifacts/15022229992) contains 14 actual Chromium captures, including the staff and patient sign-in screens, dashboard, chart, directory, coded health record, prior imaging, vaccination history, settings and mobile workflows. These are rendered application captures, not mockups. The archive is retained for 30 days; the [frontend screenshot instructions](frontend/README.md#capture-reference-screenshots) explain how to reproduce it. Current main-branch runs also publish the `emr-workspace-screenshots` artifact.

## Repository guide

| Path | Purpose |
| --- | --- |
| `frontend/` | React application, shared styles, staff and patient views, frontend tests |
| `backend/` | FastAPI routes, models, migrations, clinical workflow logic and tests |
| `scripts/` | Reference imports, runtime packaging, security review and browser verification |
| [docs/UX_DESIGN.md](docs/UX_DESIGN.md) | Design rationale and references |
| [docs/UX_AUDIT.md](docs/UX_AUDIT.md) | Incremental and final release evidence |
| [docs/SYNTHETIC_POPULATION.md](docs/SYNTHETIC_POPULATION.md) | Fictional patient generation and history |
| [docs/ICD10_REFERENCE.md](docs/ICD10_REFERENCE.md) | Diagnosis terminology |
| [docs/MEDICATION_VACCINE_REFERENCE.md](docs/MEDICATION_VACCINE_REFERENCE.md) | Medication and immunization terminology |
| [docs/CLINICAL_SECURITY_REVIEW_2026-11-25.md](docs/CLINICAL_SECURITY_REVIEW_2026-11-25.md) | Dependency findings and remediation |
| [docs/USABILITY_TEST_PROTOCOL.md](docs/USABILITY_TEST_PROTOCOL.md) | Manual accessibility and user-test procedures |
| [docs/WORKFLOWS.md](docs/WORKFLOWS.md) | API behavior, access and lifecycle rules |
| [docs/V1_RELEASE.md](docs/V1_RELEASE.md) | Historical V1 scope |
| `demo/` | Historical static preview, not the current live application |

## Safety and known limitations

- Only fictional records belong in the application, repository, screenshots and logs.
- The public workspace is disposable and has no durable shared storage. Its browser-side checks are not production security controls.
- The local API has authorization, session revocation, chart lifecycle safeguards and privacy-minimal audit events. Neither mode has received an independent penetration test or HIPAA compliance assessment. Passing advisory scans do not rule out unknown vulnerabilities.
- Manual screen-reader speech testing and representative clinician/patient usability evaluation remain outstanding. Mobile worklists and charts still require substantial vertical scrolling. Automated checks do not establish full WCAG conformance.
- Patient histories and imaging findings are fictional and not independently physician-validated. Imaging records contain report text, not diagnostic images or PACS/DICOM integration. Historical background and imaging records are read-only in this release.
- Terminology lookup is not electronic prescribing, dosing or interaction checking, clinical decision support, vaccine eligibility forecasting or registry reporting. Real billing, insurance claims, secure messaging and external clinical integrations are outside scope.

The repository is public; third-party packages retain their own licenses. Distributed notices are included with the public build at [third-party-notices](https://ai-cj.github.io/primary-care-emr/third-party-notices/README.txt). No repository-level license is declared.

## Why I built it

I started this project to learn how a larger software system is built from the ground up. Small exercises rarely show how data models, clinical workflows, migrations, validation, tests and user interfaces depend on one another. This project brings those problems together in one system.
