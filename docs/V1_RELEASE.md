# V1.0.0 release record

**Released:** November 24, 2026  
**Tagged commit:** [`492fd02`](https://github.com/AI-CJ/primary-care-emr/commit/492fd02a1e26a4e15b8532e8028fdcc59547f37e)  
**Release:** [v1.0.0](https://github.com/AI-CJ/primary-care-emr/releases/tag/v1.0.0)

> This is the historical record of the original tagged release, not a description of today's public interface. The subsequent browser-based clinical workspace and UX redesign are documented in the [README](../README.md), [design rationale](UX_DESIGN.md) and [release audit](UX_AUDIT.md). The V1 tag is unchanged.

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

At this release, GitHub Pages published a static, read-only presentation. The complete API-backed application was available for local execution. The current public site has since replaced the static presentation with the React interface and clinical routes running in an isolated browser worker; it does not connect to an external clinical database.

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

Release checks for the original V1.0.0 tag:

- [x] the latest verified `main` commit passes GitHub Actions;
- [x] the Alembic upgrade chain succeeds against PostgreSQL;
- [x] backend tests pass;
- [x] frontend lint, tests, and production build pass;
- [x] authenticated staff and patient boundaries are verified;
- [x] archived charts reject active mutation paths while retaining history;
- [x] the static public artifact deployed successfully through GitHub Pages;
- [x] keyboard, reduced-motion, responsive, and basic contrast checks are complete;
- [x] setup and workflow checks run successfully from clean CI checkouts;
- [x] known limitations remain visible in the repository and demo;
- [x] the `v1.0.0` release tag points to the verified deployed commit.

The original [verification run](https://github.com/AI-CJ/primary-care-emr/actions/runs/45463209604) succeeded. [Pages deployment 45463610626](https://github.com/AI-CJ/primary-care-emr/actions/runs/45463610626) succeeded on its second attempt after Pages was enabled; the V1 release was published on November 24, 2026. This establishes successful deployment, not an independent visual inspection of the historical live site. Subsequent application releases deploy from verified main commits while retaining the original tag.

## Post-V1 work

Future development may include a production hosting reference architecture, stronger operational audit retention, formal manual accessibility testing, patient correction requests, records export, FHIR mappings, secure messaging, billing demonstrations, and additional primary-care workflows. Those items are not required to represent this synthetic portfolio V1 honestly.
