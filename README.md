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
| Patient portal | Staff preview for nine clinical areas; authenticated patient sign-in with patient-scoped appointments, finalized visits, conditions, medication history, allergies, recent vitals, care goals, lab requests/released results, and referrals |

The staff side is the most complete part of the project. The signed-in patient portal currently shows appointments, finalized visits, health conditions, medication history, allergies, recent vitals, care goals, lab requests/released results, and referrals; the staff-only preview uses separate chart-scoped routes. Clinical information remains read-only; signed-in patients can submit appointment change requests and save their own communication preferences. Staff previews remain separate from the patient portal.

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

Both account commands prompt for a local-only password. The patient command links an account to an existing synthetic chart; replace patient ID 1 with an ID from your own seed records if needed. Do not use real patient data or a real clinical password. Only clinicians and administrators can enter the staff workspace. Patient accounts can sign in to a separate portal for read-only clinical summaries (appointments, finalized visits, conditions, medications, allergies, vitals, care goals, labs, referrals) and their own editable communication preferences.

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
npm test
npm run build
```

GitHub Actions runs the backend test suite and frontend build on pushes to `main` and on pull requests.

The current tests cover appointment rules, visit note behavior, care goals, follow up tasks, labs, referrals, the patient timeline, patient-account bootstrap, and patient portal access limits.

## Data safety

This repository uses synthetic data only.

Do not add real patient names, dates of birth, contact details, medical histories, medications, lab results, insurance information, billing information, identifiers, screenshots, or logs.

The project models health care workflows, but it does not claim to be HIPAA compliant or ready for a real clinic.

Authentication responses and clinical API responses, including access denials, send `Cache-Control: no-store` to discourage HTTP caches from retaining tokens, account details, or patient records. This complements server-side authorization; it is not a substitute for secure transport or production security review.

Authentication outcomes and clinical endpoint access now produce durable audit events
containing a timestamp, event type, HTTP method/status, a route template, and,
when applicable, an actor account ID and numeric resource/patient IDs.
Failed logins do not retain the submitted username. The audit table never stores
passwords, bearer tokens, query strings, request bodies, clinical text, IP
addresses, or raw URLs. Events cannot be edited or deleted through the API,
but database administrators could change them; this is not a tamper-proof or
compliance-ready audit solution. Unexpected exceptions raised by clinical endpoint handlers are recorded as
HTTP 500 events without storing exception messages or clinical content.
Authentication failures and other errors outside the clinical dispatch path
are not all covered, and clinical changes and their HTTP audit events do not
share a database transaction. A read-only `GET /admin/audit-events` endpoint lets authenticated administrators
review this minimal metadata, newest first, with a bounded `limit` (1–100),
`before_id` cursor and optional `event_type` filter. Clinicians, front desk
accounts and patients cannot use it. Audit reviews and denied attempts are
themselves logged, and the response is marked `no-store`. Administrators can
also download one page at a time as a CSV attachment using
`GET /admin/audit-events/export` with the same filters and a 100-row maximum.
Exports contain the same limited metadata, are audited, and use `no-store` and
`nosniff` headers. This is not a bulk backup or an immutable evidence store. Create a
local administrator with `python -m backend.bootstrap_staff --username demo.admin --role admin`.

An administrator-only `GET /admin/audit-events/activity?hours=24` endpoint
also summarizes recent event volume, failed logins, denied access, and HTTP
server errors. Its window can be set to 1–168 hours, and the response contains
no account, route, or patient identifiers. Review requests are audited and
marked `no-store`. This is a historical summary, not an alerting service,
intrusion detector, or incident response system.

Production retention, active security alerting, and an operationally reviewed
bulk archival/export process remain open release tasks.

The patient portal also supports `GET` and `PUT /portal/communication-preferences`
for a full replacement of preferred contact method (`portal`, `phone`, or
`email`) and opt-in choices for appointment reminders and general care
updates. Patient identity is derived from their authenticated session; no
patient ID is accepted as an input. Defaults are opt-out and do not create a
database row until the patient saves. Only these preferences are mutable;
clinical records remain read-only. This demo stores preferences but does
not send email, SMS, phone messages, notifications, or reminders.


### Patient appointment change requests (API)

An authenticated patient can request a cancellation or reschedule of one of their
own current or future scheduled appointments. Requests are a separate, persistent
administrative queue: they do not change the appointment itself. Each request has
a constrained action choice, without clinical free-text; duplicate pending requests
for one appointment are prevented with a database constraint.

Patients can POST to /portal/appointment-change-requests with appointment_id
and kind (cancel or reschedule), and GET the same route to see only their own
request history. Clinicians and administrators can GET
/worklists/appointment-change-requests (oldest 100 pending requests) and POST
/appointment-change-requests/{request_id}/review to mark a request reviewed.
Review means acknowledged, not fulfilled: staff must change the schedule using
the existing appointment workflow. The patient portal now has a request form and status history, and the staff
workspace has an appointment-request queue with chart links and acknowledgment
controls. Submitting or reviewing a request does not alter a scheduled visit.
The patient form offers only eligible scheduled visits without another pending
request; the server independently checks ownership and eligibility. Staff
must make any scheduling changes separately in the patient chart. Notifications
and automatic scheduling actions remain out of scope. This is not an
emergency communications service.

### Patient chart archive and reactivation (API)

Administrators can POST to `/patients/{patient_id}/archive` and
`/patients/{patient_id}/reactivate`. Archive preserves the complete chart
and append-only lifecycle events, refuses charts with scheduled or checked-in
appointments, and revokes any existing patient portal sessions. Archived
patients cannot sign in to the portal or receive newly bootstrapped portal
accounts. Reactivation does not restore revoked sessions: the patient must
sign in again. Admins can review up to 100 newest lifecycle events via
`GET /patients/{patient_id}/lifecycle`; other roles cannot access these
administrative controls. Staff chart reads remain available for historical
review, and patient responses expose `archived_at` to identify inactive
charts. These are synthetic records; no deletion is performed.

Archived charts now reject staff demographic edits and all appointment
creation, rescheduling, and status actions with HTTP 409. Those writes and
archive/reactivation share a locked patient row, so scheduling cannot race
archival on PostgreSQL. Historical chart and appointment reads remain available.
Care goal creation, completion, discontinuation and progress updates also reject
archived charts. Archived care goals are hidden from the active-goals worklist,
while their historical chart and progress reads remain available. Follow-up task
creation, completion, cancellation, and due-date changes also reject archived
charts; the open follow-up worklist excludes archived patients without altering
task history or due-date change records. Lab order creation, cancellation, result
recording and result release also reject archived charts. Pending orders and
unreleased results for archived charts are hidden from their active worklists;
historical orders and results remain readable and reactivation restores access.
Referral creation, cancellation, and completion likewise reject archived charts;
pending referrals from archived patients are excluded from the worklist while
historical referral reads remain available. Reactivation restores referral writes.
Patient-level problem, medication, allergy, and vital creation and updates also
reject archived charts with HTTP 409 using the same patient-row lock. Historical
reads remain available, and reactivation restores these writes.
Standalone and appointment-linked visit note creation, draft edits,
finalization and addendum creation also reject archived charts. These writes
lock the patient before the visit row, preserve historical reads and retain
finalized-note immutability after reactivation.
Clinical-record links and unlinks for problems, medications, allergies, and vitals
also reject archived charts. Patient appointment change submissions and staff review
take the chart lock, preserve request history, and exclude archived charts from the
pending queue. The staff overview exposes chart status and explicit administrator-only
archive/reactivation confirmation controls.
Patient portal account creation, successful login, and preference writes coordinate
with archival using the same patient-row lock. Preference writes are refused for
archived charts even if authorization was checked earlier in the request.
These lifecycle safeguards are not a complete clinical-record retention policy.

## Project status

The main staff EMR is close to the planned portfolio V1. Recent work has focused on tightening appointment and visit workflows, limiting what the patient portal can see, and adding tests around clinical rules.

See [Portfolio V1 release boundary](docs/V1_RELEASE.md) for the acceptance checklist,
verification commands, and known limitations. A separate static, read-only synthetic
demo is prepared in `demo/`. GitHub Pages deployment requires enabling the repository's
Pages source: open [Settings → Pages](https://github.com/AI-CJ/primary-care-emr/settings/pages)
and select **GitHub Actions** under Build and deployment → Source. Once enabled,
run the [Deploy public demo workflow](https://github.com/AI-CJ/primary-care-emr/actions/workflows/pages.yml).
The intended site is https://ai-cj.github.io/primary-care-emr/; it is not a verified
live deployment until it is reachable. The static site does not connect to the clinical API.

Live e prescribing, real insurance claims, outside EHR connections, and real patient data are outside the scope of this project.

## Why I built it

I started this project because I wanted to learn how a larger software system is built from the ground up.

Small coding exercises are useful, but they do not show what happens when data models, workflows, migrations, validation, tests, and user screens all depend on each other. This project gives me a place to work through those problems in one system and document what I learn along the way.
