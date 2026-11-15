# Primary Care EMR

A full-stack primary-care electronic medical record project built to model realistic outpatient workflows using **synthetic patient data only**.

The project started as a small patient-search exercise and has grown into a working longitudinal chart with scheduling, visit documentation, labs, referrals, care planning, staff worklists, and a read-only patient portal preview.

> **Portfolio / educational project only.** This application is not certified for clinical use and must not be used with real patient information.

## What the project does today

### Patient registry and chart
- Search patients by legal or preferred name
- Create and edit synthetic patient demographics
- Record preferred names, pronouns, and sex assigned at birth
- Open a longitudinal patient chart
- View a combined clinical activity timeline

### Clinical history
- Problem list with active and resolved conditions
- Medication list with active, completed, and discontinued medications
- Allergy list with reaction, severity, and status
- Longitudinal vital-sign history
- Care goals with progress updates and completion/discontinuation states
- Follow-up tasks linked to patients and care goals

### Appointments and clinic workflow
- Schedule patient appointments
- Prevent overlapping appointments
- Reschedule appointments
- Check patients in
- Mark appointments completed, cancelled, or no-show
- Preserve appointment status-change history
- Prevent invalid lifecycle changes, including premature check-in/no-show actions
- View the daily clinic schedule
- Review past appointments that still need staff action
- Start or open visit notes directly from appointment workflows

### Visit documentation
- Create visit notes tied to patient appointments
- Link problems, medications, allergies, and vitals to a visit
- Keep appointment-linked visit dates stable
- Finalize visit notes
- Prevent silent edits to finalized notes
- Add append-only addenda after finalization
- Record patient-facing instructions before finalizing a visit

### Labs and referrals
- Create lab requests during visits
- Record lab results
- Cancel pending requests
- View patient lab history across visits
- Maintain pending-lab and unreleased-result staff worklists
- Require staff review before releasing results to the portal preview
- Create, cancel, and complete specialist referrals
- View referral history across visits
- Maintain a pending-referrals worklist

### Staff worklists
- Daily clinic schedule
- Past appointments needing status review
- Pending lab requests
- Lab results waiting for portal release
- Pending referrals
- Active care goals
- Open follow-up tasks

### Patient-facing preview
A read-only patient portal preview is being developed separately from the staff chart. Current patient-facing views include:
- Medications
- Problems
- Allergies
- Recent vitals
- Care goals
- Upcoming and recent appointments
- Finalized visit summaries
- Lab requests and released lab results
- Referral summaries

The portal endpoints intentionally expose smaller patient-facing response models instead of returning the full staff record.

## Technology

### Frontend
- React 19
- TypeScript
- Vite
- CSS
- ESLint

### Backend
- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

### Data and development infrastructure
- PostgreSQL 17
- Docker Compose
- psycopg
- GitHub Actions

## Architecture

The project is split into a React frontend and FastAPI backend:

```text
React + TypeScript
        |
        | HTTP / JSON
        v
FastAPI + Pydantic
        |
        | SQLAlchemy
        v
PostgreSQL
```

Alembic migrations are used for database schema changes rather than modifying the database manually.

As the application has grown, larger workflow areas have been separated into backend modules such as scheduling, encounters, labs, referrals, care goals, follow-up tasks, patient timeline, and portal-specific data views.

## Synthetic-data rule

**No real protected health information belongs in this repository or application.**

Do not use real:
- patient names
- dates of birth
- addresses or contact information
- medical histories
- medications
- lab results
- insurance information
- billing information
- identifiers
- screenshots or logs containing patient data

All development, tests, demonstrations, screenshots, and seed records must use fictional data.

The architecture and workflows may model healthcare behavior, but this repository is not a claim of HIPAA compliance or clinical-production readiness.

## Local development

### Prerequisites

You will need:
- Python 3.12
- Node.js
- npm
- Docker
- Docker Compose
- Git

### 1. Clone the repository

```bash
git clone https://github.com/AI-CJ/primary-care-emr.git
cd primary-care-emr
```

### 2. Create the local environment file

```bash
cp .env.example .env
```

The example configuration is:

```env
POSTGRES_DB=emr
POSTGRES_USER=emr_user
POSTGRES_PASSWORD=change_me
```

Use a development-only password in your local `.env`. The real `.env` file is ignored by Git.

### 3. Start PostgreSQL

```bash
docker compose up -d
```

### 4. Create the Python virtual environment

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
```

### 5. Apply database migrations

```bash
alembic upgrade head
```

### 6. Seed synthetic patients

```bash
python -m backend.seed
```

The seed script is intentionally safe to run more than once; it skips seeding when patient data already exists.

### 7. Start the backend

From the repository root with the virtual environment active:

```bash
uvicorn backend.main:app --reload
```

The API runs at:

```text
http://127.0.0.1:8000
```

FastAPI's interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

### 8. Start the frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite will print the local frontend URL, normally:

```text
http://localhost:5173
```

## Tests and checks

### Backend tests

From the repository root with the virtual environment active:

```bash
python -m unittest discover -s backend/tests -p 'test_*.py'
```

The backend test suite currently covers major workflow rules including appointments, encounters, care goals, follow-up tasks, labs, referrals, portal-preview boundaries, timeline behavior, and clinical record invariants.

### Frontend checks

```bash
cd frontend
npm run lint
npm run build
```

### Continuous integration

GitHub Actions runs:
- the backend unit-test suite
- the production frontend build

on pushes to `main` and on pull requests.

## Project principles

The project is being built around a few rules:

- **Longitudinal care first.** Important information should remain understandable across visits.
- **Clinical history should not silently disappear.** Finalized notes use addenda rather than silent rewriting, and status histories are preserved where they matter.
- **Patient-facing data is a separate concern.** Staff records are not simply dumped into the portal.
- **Use safe defaults.** Invalid appointment transitions, impossible date sequences, and other inconsistent states should be rejected.
- **Build vertically.** Features are added as complete workflows across the database, API, and interface rather than as disconnected mock screens.
- **Keep the demo synthetic.** Real patient data is outside the scope of this repository.

## Current status

The core staff-facing EMR is well developed and includes most of the major clinical workflow foundation for the portfolio V1.

Current work is focused on finishing and hardening the remaining release areas, including:
- patient-facing portal experience
- authorization and audit behavior
- remaining communication/document/billing simulations where appropriate for V1
- accessibility and responsive UX review
- deployment configuration
- final visual polish and release documentation

This project intentionally does **not** attempt live e-prescribing, insurance claims adjudication, external EHR integration, or use of real patient data.

## Repository structure

```text
primary-care-emr/
├── backend/
│   ├── migrations/        # Alembic database migrations
│   ├── tests/             # Backend unit tests
│   ├── main.py            # FastAPI routes
│   ├── models.py          # SQLAlchemy database models
│   ├── schemas.py         # Pydantic request/response models
│   └── ...                # Workflow modules
├── frontend/
│   └── src/
│       ├── components/    # React workflow and chart components
│       ├── App.tsx
│       ├── App.css
│       └── types.ts
├── .github/workflows/     # CI checks
├── compose.yaml           # Local PostgreSQL container
├── alembic.ini
└── README.md
```

## Why I am building this

This project is both a software-engineering portfolio project and a way to learn how a larger system evolves beyond isolated coding exercises.

The goal is not just to produce screens that look like an EMR. It is to work through the engineering decisions behind a system with real relationships, workflow states, historical records, validation rules, testing, migrations, and distinct staff and patient experiences.
