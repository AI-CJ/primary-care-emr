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
- PostgreSQL migrations, automated backend tests, frontend lint/tests, and production builds.

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

The GitHub Actions `Checks` workflow repeats the migration check, backend suite, frontend lint, frontend tests, and production build on pull requests and pushes to `main`.

## Synthetic account setup

Create local-only demo accounts after seeding:

```bash
python -m backend.bootstrap_staff --username demo.clinician --role clinician
python -m backend.bootstrap_staff --username demo.admin --role admin
python -m backend.bootstrap_patient --username demo.patient --patient-id 1
```

Each command prompts for a password. Use credentials made only for local demonstration. Do not reuse a real password.

## Safety and privacy limits

V1 includes server-side authentication, patient ownership checks, clinical-role restrictions, no-store response headers, and privacy-minimal audit metadata. These controls are meaningful engineering safeguards, but they are not a claim of HIPAA compliance or production readiness.

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

A V1 release is ready when:

- [ ] the latest `main` commit passes GitHub Actions;
- [ ] the Alembic upgrade chain succeeds against PostgreSQL;
- [ ] backend tests pass;
- [ ] frontend lint, tests, and production build pass;
- [ ] authenticated staff and patient boundaries are verified;
- [ ] archived charts reject all active mutation paths while retaining history;
- [ ] the static public demo is reachable and clearly labeled;
- [ ] keyboard, reduced-motion, responsive, and basic contrast checks are complete;
- [ ] README setup steps work from a clean clone;
- [ ] known limitations remain visible in the repository and demo;
- [ ] a release tag is created from the verified commit.

## Post-V1 work

Future development may include a production hosting reference architecture, stronger operational audit retention, formal accessibility testing, browser-level end-to-end automation, patient correction requests, records export, FHIR mappings, secure messaging, billing demonstrations, and additional primary-care workflows. Those items are not required to represent this synthetic portfolio V1 honestly.
