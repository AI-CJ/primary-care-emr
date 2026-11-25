# Primary Care EMR

[![Checks](https://github.com/AI-CJ/primary-care-emr/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/AI-CJ/primary-care-emr/actions/workflows/checks.yml)

Primary Care EMR is a full-stack electronic medical record and patient portal for a fictional outpatient primary care practice. It brings scheduling, longitudinal charts, visit documentation, clinical orders and care coordination together in a single application.

**[Open the live application](https://ai-cj.github.io/primary-care-emr/)** · [Design rationale](docs/UX_DESIGN.md) · [Engineering audit](docs/UX_AUDIT.md)

> Educational portfolio project. All patient records are fictional. Do not enter real patient information or personal credentials. Neither the public nor local application is approved for clinical use.

## Try the application

| Role | Explore |
| --- | --- |
| Administrator | Clinical workflows, chart archive/reactivation, audit activity and CSV export |
| Clinician | Daily schedule, patient records, visit notes, clinical orders and care tasks |
| Patient | Upcoming appointments, health records, shared results, care goals and communication preferences |

Select a staff account, or use **Switch to patient sign-in** to open the portal as Jordan Lee or Maria Thompson. The public workspace prepares its Python runtime while the sign-in page is open. Wait for **Workspace ready** if you want to avoid most of the initialization delay after clicking an account.

Changes remain in the same tab when you switch accounts. Use **Demo reset** in the legal notice to restore the starting records. Refreshing or closing the tab also clears changes. No orders, messages or referrals are transmitted to outside services.

## What the application does

### Clinical workspace

- Dashboard with today's schedule and outstanding work queues drawn from the API, rather than hard-coded counts.
- Searchable patient directory and chart sections for the clinical summary, health record, appointments, visit notes, labs/referrals and care plan.
- Patient identity, recorded allergy status, active problems and medications, the latest dated vital record and a longitudinal activity timeline.
- Appointment scheduling, conflict detection, rescheduling, check-in, completion, cancellation and no-show tracking.
- Staff ICD-10-CM lookup by diagnosis description or code, with explicit problem-linked medication and lab indications.
- Structured visit notes, linked clinical-record snapshots, draft review, finalization, append-only addenda and patient-facing instructions.
- Lab requests and results, explicit result release, referral follow-up, care goals, task tracking and staff worklists.
- Administrator-only chart archive/reactivation and audit review, with historical clinical records retained.

### Patient portal

The patient portal has its own lighter visual treatment, larger controls and plain-language navigation. Home highlights the next recorded appointment and common tasks; separate sections cover health records, appointments and visits, test results and referrals, care plans, and settings.

Patients can review their own clinical history, distinguish current and historical medications, view results shared by the clinic, submit appointment change requests and save communication preferences. Clinical records are read-only from the patient account. An appointment request does not change the appointment until staff act. Staff also have a chart-scoped read-only preview of the portal.

### Design and accessibility

The clinical and patient interfaces use a shared palette of gunmetal, emerald and sea-glass colors, with original inline SVG artwork. The clinician view favors compact information and predictable navigation; the patient view favors readability, explicit task labels and generous touch targets. Design decisions draw on health IT usability research and WCAG 2.2. See the [design rationale](docs/UX_DESIGN.md) for implementation choices and references. Full accessibility conformance has not been established.

## Architecture

The same React frontend and FastAPI clinical routes support two execution modes. The public site does not require a hosted database.

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
| Public runtime | Pyodide, WebAssembly, Web Worker, SQLite |
| Development and delivery | Docker Compose, GitHub Actions, GitHub Pages |
| Verification | Python unittest, Node test runner, ESLint, TypeScript, Playwright/Chromium |

The API-backed application uses server-side authorization and database transaction safeguards. The public build exercises the same route logic and validations in a browser worker, but its local role checks are illustrative rather than a security boundary against someone controlling their own browser. SQLite uses ORM metadata and serialized requests, not PostgreSQL's migration and concurrency guarantees.

## Run locally

Use Python 3.12, Node.js 22 (a current 22.x release), npm, Git, Docker and Docker Compose. The commands below use a Linux/WSL shell, as in the development environment.

### 1. Prepare the database

```bash
git clone https://github.com/AI-CJ/primary-care-emr.git
cd primary-care-emr
cp .env.example .env
```

Replace the example password in `.env` with a local-only value. The file is ignored by Git. Start PostgreSQL and confirm the database is ready:

```bash
docker compose up -d
docker compose exec database sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### 2. Start the backend

From the repository root:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m scripts.prepare_icd10_catalog
alembic upgrade head
python -m backend.seed
python -m backend.bootstrap_staff --username demo.clinician --role clinician
python -m backend.bootstrap_staff --username demo.admin --role admin
python -m backend.bootstrap_patient --username demo.patient --patient-id 1
uvicorn backend.main:app --reload
```

The catalog preparation step imports the reviewed official FY 2027 ICD-10-CM descriptions. The resulting local reference contains 74,879 reportable codes, with a verified SHA-256 digest. See the [diagnosis reference](docs/ICD10_REFERENCE.md) for provenance, refresh instructions and limitations.

Account setup prompts for passwords (12–128 characters). The patient ID example assumes a fresh database seeded by this project; confirm the chart ID before linking an account if the database already contains records. The local seed creates three fictional patients, while the public workspace provides a richer pre-populated clinical dataset.

API: `http://127.0.0.1:8000` · OpenAPI documentation: `http://127.0.0.1:8000/docs`.

### 3. Start the frontend

In another terminal, from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173` and sign in with a local account. See the [frontend guide](frontend/README.md) for build modes and the [workflow reference](docs/WORKFLOWS.md) for route behavior and configuration.

### Reproduce the public browser build

From the repository root, with Python and Node.js available:

```bash
python scripts/build_browser_runtime.py
cd frontend
npm ci
VITE_EMR_BROWSER=1 npm run build
npm run preview
```

Open the local URL printed by Vite. No PostgreSQL service is required for this build. Runtime assets are prepared from pinned package versions; the packaged API runs in the tab rather than using a remote clinical server.

## Testing and deployment

```bash
# From the repository root, with the Python environment active
python -m unittest discover -s backend/tests -p 'test_*.py'

# Frontend checks
cd frontend
npm ci
npm run lint
npm test
npm run build
```

Use only a disposable test database when exercising database-backed tests and browser workflows. The [CI workflow](.github/workflows/checks.yml) specifies the PostgreSQL test settings, migration checks and browser commands for both execution modes.

The redesigned application at commit [`5a52bb8`](https://github.com/AI-CJ/primary-care-emr/commit/5a52bb84e2e86148cd228e4239e47c696a5e0a24) passed all five CI jobs: 376 backend tests, 33 frontend tests, the migration chain, lint/build, and the browser workflow checks. GitHub Pages successfully deployed that commit on November 24, 2026 (Eastern time).

[Verification run](https://github.com/AI-CJ/primary-care-emr/actions/runs/45546235206) · [Deployment run](https://github.com/AI-CJ/primary-care-emr/actions/runs/45546500308) · [Audit details](docs/UX_AUDIT.md)

The public build initializes a 19.4 MiB runtime package (before transfer compression). Startup preparation begins before sign-in. CI measurements ranged from 6.97 to 10.07 seconds for fresh-tab preparation and 0.39 to 0.88 seconds for sign-in once prepared. These are two local CI observations, not a public-network performance benchmark.

## Reference screenshots

The browser workflow captures the actual rendered application using the fictional records in an isolated tab. Open a successful [Checks run](https://github.com/AI-CJ/primary-care-emr/actions/workflows/checks.yml?query=branch%3Amain) and download its `emr-workspace-screenshots` artifact for the staff sign-in, dashboard, patient chart and patient portal views. These are rendered application captures, not design mockups. Artifacts are retained for 30 days; the [frontend guide](frontend/README.md#capture-reference-screenshots) explains how to reproduce them.

## Repository guide

| Path | Purpose |
| --- | --- |
| `frontend/` | React application, shared styles, staff and patient views, frontend tests |
| `backend/` | FastAPI routes, models, schemas, authentication, clinical workflow logic and backend tests |
| `scripts/` | Browser runtime packaging and end-to-end verification |
| `docs/UX_DESIGN.md` | Research-informed design choices |
| `docs/UX_AUDIT.md` | Audit findings, test evidence and release verification |
| `docs/USABILITY_TEST_PROTOCOL.md` | Reproducible manual screen-reader and formative user-test procedures |
| `docs/WORKFLOWS.md` | API contracts, access rules, lifecycle behavior and hosting configuration |
| `docs/V1_RELEASE.md` | Historical scope of the tagged V1 release |
| `demo/` | Historical static preview, retained for reference; not the deployed application |

## Safety and known limitations

- Only fictional records belong in the application, logs, screenshots and repository.
- The public workspace is disposable and has no durable shared storage. Its browser-side access checks are not production-grade security.
- The API-backed build models role restrictions, session revocation, chart lifecycle safeguards and privacy-minimal audit events. It has not undergone a clinical security review, penetration test or HIPAA compliance assessment.
- The November 25 dependency review resolved the 11 reported npm toolchain advisories using compatible lockfile updates. The reviewed lockfile returned zero advisories in the full and production-only npm scans. CI now archives both reports and rejects unresolved npm advisories. This is not a Python dependency audit, penetration test, or assurance against unknown vulnerabilities.
- Manual screen-reader evaluation and representative clinician/patient usability sessions remain outstanding. Automated Chromium accessibility-tree and reflow checks complement the [manual test protocol](docs/USABILITY_TEST_PROTOCOL.md); the deployment workflow also verifies the served revision and isolated account workflows. These checks do not establish clinical readiness or complete accessibility conformance.
- Real prescribing, insurance claims, billing, secure messaging, external clinical integrations and clinical decision support are outside the current release scope.

The repository is public; established frameworks and runtime packages retain their own licenses. No repository-level license is declared. See [workflow details](docs/WORKFLOWS.md) and the [audit](docs/UX_AUDIT.md) for more information.

## Why I built it

I started this project to learn how a larger software system is built from the ground up. Small exercises rarely show how data models, clinical workflows, migrations, validation, tests and user interfaces depend on one another. This project brings those problems together in one system.
