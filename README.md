# Primary Care EMR

[![Checks](https://github.com/AI-CJ/primary-care-emr/actions/workflows/checks.yml/badge.svg)](https://github.com/AI-CJ/primary-care-emr/actions/workflows/checks.yml)

Primary Care EMR is a full stack portfolio project that models the day to day work of a small outpatient clinic.

It includes patient charts, scheduling, visit notes, labs, referrals, care goals, staff worklists, and a separate patient portal preview. All patient records in the project are fictional.

> This project is for learning and portfolio use. It is not approved for real clinical use and must not be used with real patient information.

## At a glance

| Area | What works now |
| --- | --- |
| Patient chart | Demographics, problems, medications, allergies, vitals, care goals, follow up tasks, and a clinical timeline |
| Scheduling | Appointments, rescheduling, conflict checks, check in, completion, cancellation, no show, and daily schedule views |
| Visit notes | Appointment linked notes, clinical data links, finalization, addenda, and patient instructions |
| Labs | Lab requests, results, cancellation, history, staff review, and release to the portal preview |
| Referrals | New referrals, cancellation, completion, history, and a pending referral worklist |
| Staff worklists | Daily schedule, past appointments, pending labs, unreleased results, pending referrals, active goals, and open follow ups |
| Patient portal | Staff preview for nine clinical areas; authenticated patient sign-in and patient-scoped appointment view |

The staff side is the most complete part of the project. The signed-in patient portal currently shows appointments only; the staff-only preview covers more clinical areas. Both remain read-only and are deliberately separate from the staff chart.

## How it fits together

The browser talks to a FastAPI backend over HTTP. FastAPI validates requests with Pydantic, SQLAlchemy handles database access, and PostgreSQL stores the data.

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

Database changes are tracked with Alembic migrations. Larger backend workflows have their own modules instead of living in one large file.

## Stack

| Layer | Tools |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, CSS |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy |
| Database | PostgreSQL 17, psycopg |
| Database changes | Alembic |
| Local services | Docker Compose |
| Checks | GitHub Actions, Python unit tests, ESLint, TypeScript build |

## Run it locally

You will need Python 3.12, Node.js, npm, Docker, Docker Compose, and Git.

### Clone the project

```bash
git clone https://github.com/AI-CJ/primary-care-emr.git
cd primary-care-emr
```

### Set up PostgreSQL

Create your local environment file from the example.

```bash
cp .env.example .env
```

The example uses:

```env
POSTGRES_DB=emr
POSTGRES_USER=emr_user
POSTGRES_PASSWORD=change_me
```

Use a password made only for local development. The real `.env` file is ignored by Git.

Start PostgreSQL with Docker Compose.

```bash
docker compose up -d
```

### Set up the backend

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
alembic upgrade head
python -m backend.seed
python -m backend.bootstrap_staff --username demo.clinician --role clinician
python -m backend.bootstrap_patient --username demo.patient --patient-id 1
uvicorn backend.main:app --reload
```

Both account commands prompt for a local-only password. The patient command links an account to an existing synthetic chart; replace patient ID 1 with an ID from your own seed records if needed. Do not use real patient data or a real clinical password. Only clinicians and administrators can enter the staff workspace. Patient accounts can sign in to the separate read-only appointment portal.

The API runs at `http://127.0.0.1:8000`.

FastAPI docs are available at `http://127.0.0.1:8000/docs`.

### Set up the frontend

Open another terminal.

```bash
cd frontend
npm ci
npm run dev
```

Vite normally starts the frontend at `http://localhost:5173`.

## Tests

Run the backend tests from the repository root while the Python virtual environment is active.

```bash
python -m unittest discover -s backend/tests -p 'test_*.py'
```

Run the frontend checks from the `frontend` folder.

```bash
npm run lint
npm run build
```

GitHub Actions runs the backend test suite and frontend build on pushes to `main` and on pull requests.

The current tests cover appointment rules, visit note behavior, care goals, follow up tasks, labs, referrals, the patient timeline, patient-account bootstrap, and patient portal access limits.

## Data safety

This repository uses synthetic data only.

Do not add real patient names, dates of birth, contact details, medical histories, medications, lab results, insurance information, billing information, identifiers, screenshots, or logs.

The project models health care workflows, but it does not claim to be HIPAA compliant or ready for a real clinic.

## Project status

The main staff EMR is close to the planned portfolio V1. Recent work has focused on tightening appointment and visit workflows, limiting what the patient portal can see, and adding tests around clinical rules.

The remaining work is mostly release work. That includes access and audit controls, final portal work, deployment, accessibility checks, mobile cleanup, visual polish, and documentation.

Live e prescribing, real insurance claims, outside EHR connections, and real patient data are outside the scope of this project.

## Why I built it

I started this project because I wanted to learn how a larger software system is built from the ground up.

Small coding exercises are useful, but they do not show what happens when data models, workflows, migrations, validation, tests, and user screens all depend on each other. This project gives me a place to work through those problems in one system and document what I learn along the way.
