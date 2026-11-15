# Primary Care EMR

This is a full stack primary care electronic medical record project. It uses **synthetic patient data only**.

The project started as a small patient search exercise. It has grown into a working EMR with patient charts, appointments, visit notes, labs, referrals, care goals, staff worklists, and a read only patient portal preview.

> **Portfolio and learning project only.** This application is not approved for real clinical use and must not be used with real patient information.

## What the project can do

### Patient registry and chart

- Search for patients by legal or preferred name
- Create and edit synthetic patient records
- Record preferred names and pronouns
- Record sex assigned at birth
- Open a patient chart
- View a clinical activity timeline

### Clinical history

- Record active and resolved problems
- Record active, completed, and discontinued medications
- Record allergies, reactions, severity, and status
- Record vital signs over time
- Create care goals and update their progress
- Create follow up tasks for patients and care goals

### Appointments and clinic workflow

- Schedule appointments
- Prevent overlapping appointments
- Reschedule appointments
- Check patients in
- Mark appointments as completed, cancelled, or no show
- Keep a history of appointment status changes
- Block invalid status changes
- View the daily clinic schedule
- Review past appointments that still need staff action
- Start or open visit notes from appointment screens

### Visit notes

- Create visit notes tied to appointments
- Link problems, medications, allergies, and vitals to a visit
- Keep appointment dates fixed when a visit note is linked
- Finalize visit notes
- Prevent silent edits to finalized notes
- Add new addenda after a note is finalized
- Add patient instructions before a visit note is finalized

### Labs and referrals

- Create lab requests during visits
- Record lab results
- Cancel pending lab requests
- View lab history across visits
- View staff worklists for pending labs and results waiting for release
- Require staff review before a lab result is shown in the portal preview
- Create specialist referrals
- Cancel pending referrals
- Complete referrals
- View referral history across visits
- View a staff worklist for pending referrals

### Staff worklists

The staff side currently includes worklists for:

- today's clinic schedule
- past appointments that need review
- pending lab requests
- lab results waiting for portal release
- pending referrals
- active care goals
- open follow up tasks

### Patient portal preview

The patient portal preview is separate from the staff chart. It is read only right now.

Patients can preview:

- medications
- problems
- allergies
- recent vitals
- care goals
- upcoming and recent appointments
- finalized visit summaries
- lab requests
- released lab results
- referral summaries

The portal does not return the full staff record. It uses smaller response models that only include information meant for the patient view.

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

### Database and development tools

- PostgreSQL 17
- Docker Compose
- psycopg
- GitHub Actions

## Architecture

The project has a React frontend and a FastAPI backend.

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

Alembic handles database schema changes.

As the project has grown, larger parts of the backend have been split into separate modules. These include scheduling, visits, labs, referrals, care goals, follow up tasks, the patient timeline, and portal views.

## Synthetic data rule

**No real protected health information belongs in this project.**

Do not use real:

- patient names
- dates of birth
- addresses
- phone numbers
- email addresses
- medical histories
- medications
- lab results
- insurance information
- billing information
- patient identifiers
- screenshots or logs that contain real patient data

All development data, test data, screenshots, and demo records must be fictional.

This project models health care workflows, but it does not claim to be HIPAA compliant or ready for real clinical use.

## Local development

### What you need

Install these first:

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

The example settings are:

```env
POSTGRES_DB=emr
POSTGRES_USER=emr_user
POSTGRES_PASSWORD=change_me
```

Use a password made only for local development in your `.env` file.

The real `.env` file is ignored by Git.

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

### 6. Add the starter synthetic patients

```bash
python -m backend.seed
```

The seed script can be run more than once. It skips this step if patient data already exists.

### 7. Start the backend

From the repository root with the virtual environment active:

```bash
uvicorn backend.main:app --reload
```

The API runs at:

```text
http://127.0.0.1:8000
```

FastAPI also provides API documentation at:

```text
http://127.0.0.1:8000/docs
```

### 8. Start the frontend

Open another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite will print the local frontend address. It is usually:

```text
http://localhost:5173
```

## Tests and checks

### Backend tests

From the repository root with the virtual environment active:

```bash
python -m unittest discover -s backend/tests -p 'test_*.py'
```

The backend tests cover many of the main workflow rules. This includes appointments, visits, care goals, follow up tasks, labs, referrals, the patient timeline, and portal data limits.

### Frontend checks

```bash
cd frontend
npm run lint
npm run build
```

### GitHub Actions

GitHub Actions runs two checks on pushes to `main` and on pull requests:

- backend tests
- frontend production build

## Project rules

These are some of the main rules I am using while building the project.

- **Keep the chart useful over time.** Important information should still make sense across many visits.
- **Do not silently erase clinical history.** Finalized notes use addenda instead of silent changes. Important status changes are also kept in history.
- **Keep staff and patient views separate.** The portal should only show information meant for patients.
- **Block invalid states.** The system should reject appointment changes, dates, and other values that do not make sense.
- **Build complete workflows.** A feature should work through the database, API, and interface before I move on.
- **Use synthetic data only.** Real patient data is outside the scope of this project.

## Current status

The main staff EMR is close to complete for the portfolio V1.

The current system already includes most of the core clinical workflows. The remaining work is focused on finishing and cleaning up the release.

This includes:

- finishing the patient portal experience
- adding basic access and audit controls
- deciding which message, document, and billing features belong in V1
- checking accessibility and mobile use
- preparing deployment
- improving the final visual design
- finishing release documentation

This project does **not** include live e prescribing, real insurance claim processing, outside EHR connections, or real patient data.

## Repository structure

```text
primary-care-emr/
├── backend/
│   ├── migrations/        # Alembic database migrations
│   ├── tests/             # Backend tests
│   ├── main.py            # FastAPI routes
│   ├── models.py          # SQLAlchemy database models
│   ├── schemas.py         # Pydantic request and response models
│   └── ...                # Workflow modules
├── frontend/
│   └── src/
│       ├── components/    # React components
│       ├── App.tsx
│       ├── App.css
│       └── types.ts
├── .github/workflows/     # GitHub Actions checks
├── compose.yaml           # Local PostgreSQL container
├── alembic.ini
└── README.md
```

## Why I am building this

I am building this project to learn how a larger software system comes together.

I wanted to go beyond small coding exercises and build something with real relationships between data, workflow rules, database changes, tests, and user screens.

The goal is not just to make something that looks like an EMR. I want to understand how to plan, build, test, and improve a system like this from start to finish.
