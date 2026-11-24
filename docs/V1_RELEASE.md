# Portfolio V1 Release

Primary Care EMR V1 is a synthetic-data portfolio release that demonstrates the day-to-day workflows of a small outpatient primary care clinic. It is not approved for clinical use and must not receive real patient information.

## Release boundary

The source application includes:

- authenticated clinician, administrator, and patient accounts;
- staff patient search and demographic management;
- appointment scheduling, check-in, completion, cancellation, no-show, and daily schedules;
- structured visit notes with finalization and append-only addenda;
- problem, medication, allergy, vital, care-goal, follow-up, laboratory, and referral workflows;
- staff worklists for unresolved operational and clinical work;
- an authenticated patient portal with patient-scoped read access;
- patient communication preferences and appointment-change requests;
- privacy-minimal authentication and clinical-access audit events;
- non-destructive patient chart archive and reactivation controls;
- PostgreSQL migrations, automated backend tests, frontend lint/tests, production builds, and Chromium workflow checks.

The public GitHub Pages site is intentionally a static, read-only presentation layer. It demonstrates the product design with fictional records but does not connect to FastAPI or PostgreSQL. The complete API-backed application remains available in this repository for local execution and technical review.

## Verification

From the repository root, start PostgreSQL and prepare the backend:

```bash
docker compose up -d
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
alembic upgrade head
python -m backend.seed
```

Run backend verification:

```bash
python -m unittest discover -s backend/tests -p 'test_*.py'
```

Run frontend verification:

```bash
cd frontend
npm ci
npm run lint
npm test
npm run build
```

The GitHub Actions `Checks` workflow repeats the migration check, backend suite, frontend lint, frontend tests, and production build on pull requests and pushes to `main`. It also:

- serves the static demo and exercises its desktop and mobile workflows in Chromium;
- verifies the core demo text palette meets a 4.5:1 contrast target;
- builds the real React application against a freshly migrated and seeded disposable PostgreSQL database;
- exercises staff and patient authentication, permission boundaries, archive/reactivation persistence, archived-patient access rejection, communication preference persistence, keyboard account-mode switching, and mobile layout.

The browser jobs run from a clean GitHub Actions checkout with reduced-motion preferences and horizontal-overflow checks.

## Configuration for a hosted synthetic instance

The local defaults are unchanged, but the API and frontend can be configured without editing source code:

| Variable | Where | Meaning |
| --- | --- | --- |
| POSTGRES_HOST | Backend | Database hostname (default localhost) |
| POSTGRES_PORT | Backend | Database port (default 5432) |
| POSTGRES_SSLMODE | Backend | Optional PostgreSQL TLS mode; prefer verify-full with a trusted CA for remote databases |
| EMR_CORS_ORIGINS | Backend | Comma-separated explicit HTTP(S) frontend origins; empty disables cross-origin access |
| VITE_API_BASE_URL | Frontend build | API origin or path prefix; empty supports a same-origin reverse proxy |

Continue to supply POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD through private environment settings. Never put credentials in VITE_ variables, which are exposed in the frontend bundle. The local Compose database binds to loopback only. Run migrations as a separate release step before starting the API. For a hosted synthetic instance, configure HTTPS, restrict database networking, and use dedicated fictional accounts. The GitHub Pages demo remains independent of these settings.

These settings do not constitute a production deployment or a clinical security review.

## Synthetic account setup

Create local-only demo accounts after seeding:

```bash
python -m backend.bootstrap_staff --username demo.clinician --role clinician
python -m backend.bootstrap_staff --username demo.admin --role admin
python -m backend.bootstrap_patient --username demo.patient --patient-id 1
```

Each command prompts for a password. Use credentials made only for local demonstration. Do not reuse a real password.

## Safety and privacy limits

V1 includes server-side authentication, patient ownership checks, clinical-role restrictions, no-store response headers, privacy-minimal audit metadata, and archive-aware mutation controls. These controls are meaningful engineering safeguards, but they are not a claim of HIPAA compliance or production readiness.

The project does not include:

- real patient data or a real clinic deployment;
- live electronic prescribing;
- insurance claims or eligibility transactions;
- external laboratory, pharmacy, or EHR connections;
- immutable external audit storage or formal retention operations;
- production incident response, security monitoring, penetration testing, or compliance validation;
- a supported clinical data migration path;
- medical-device, diagnostic, or treatment-decision functionality.

## Release acceptance checklist

Verified on the release-candidate branch and current `main` history:

- [x] the latest verified `main` commit passes GitHub Actions;
- [x] the Alembic upgrade chain succeeds against PostgreSQL;
- [x] backend tests pass;
- [x] frontend lint, tests, and production build pass;
- [x] authenticated staff and patient boundaries are verified;
- [x] archived charts reject active mutation paths while retaining history;
- [ ] the static public demo is reachable and clearly labeled;
- [x] keyboard, reduced-motion, responsive, and basic contrast checks are complete;
- [x] setup and workflow checks run successfully from clean CI checkouts;
- [x] known limitations remain visible in the repository and demo;
- [ ] a release tag is created from the verified deployed commit.

The Pages workflow deploys only after the `Checks` workflow succeeds. After a successful public deployment, it creates the `v1.0.0` tag and GitHub release automatically if they do not already exist. The two unchecked items therefore depend on first-time GitHub Pages enablement and successful URL verification, not additional application development.

## Post-V1 work

Future development may include a production hosting reference architecture, stronger operational audit retention, formal manual accessibility testing, patient correction requests, records export, FHIR mappings, secure messaging, billing demonstrations, and additional primary-care workflows. Those items are not required to represent this synthetic portfolio V1 honestly.
