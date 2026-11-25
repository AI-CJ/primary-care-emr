# Workflow and API reference

This reference describes the implemented access rules and state transitions for the API-backed application and its browser-only counterpart. For setup and a product overview, start with the [README](../README.md). FastAPI exposes interactive endpoint documentation at `/docs` on the local API server.

## Data safety and access control

This repository uses synthetic data only.

Do not add real patient names, dates of birth, contact details, medical histories, medications, lab results, insurance information, billing information, identifiers, screenshots, or logs.

The project models health care workflows, but it does not claim to be HIPAA compliant or ready for a real clinic.

Authentication responses and clinical API responses, including access denials, send `Cache-Control: no-store` to discourage HTTP caches from retaining tokens, account details, or patient records. This complements server-side authorization; it is not a substitute for secure transport or production security review.

Authentication outcomes and clinical endpoint access produce audit events (durable in PostgreSQL; tab-local in the browser workspace)
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
database row until the patient saves. Patients can update these preferences and submit the appointment requests described below; clinical records remain read-only. Preferences are stored without sending email, SMS, phone messages, notifications or reminders.


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
the existing appointment workflow. The patient portal has a request form and status history, and the staff
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

Archived charts reject staff demographic edits and all appointment
creation, rescheduling, and status actions with HTTP 409. Those writes and
archive/reactivation use the same patient-row lock in PostgreSQL to coordinate scheduling with archival. Historical chart and appointment reads remain available.
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
pending queue. The staff chart exposes chart status and explicit administrator-only
archive/reactivation confirmation controls.
Patient portal account creation, successful login, and preference writes coordinate
with archival using the same patient-row lock. Preference writes are refused for
archived charts even if authorization was checked earlier in the request.
These lifecycle safeguards are not a complete clinical-record retention policy.

## Diagnosis coding and clinical indications

Clinicians and administrators can search the locally indexed FY 2027 catalog with
`POST /diagnosis-codes/search` (body `{"query":"I10"}`). Search text stays in
the API request body; the audit records the route and response status, not the
query. The patient portal cannot access this route.

Chart problems accept an optional `icd10_code`; the API validates it against
the reference and records its official description and release. Uncoded historical
records remain valid. Medication and lab order create requests accept
`problem_ids` (up to 20 distinct IDs). Medication updates preserve links if this
field is omitted or null; an empty list clears them. Staff responses expose
`indications` containing selected problem IDs, names, codes and releases.
`PUT /lab-orders/{order_id}/indications` replaces indications only for a pending
order on an unfinalized visit. All writes enforce chart ownership and archival
rules. Visit links capture the recorded coding details when linked; finalized
records are not rewritten by subsequent problem edits. Patient projections do
not expose the staff coding fields. See [ICD-10-CM reference](ICD10_REFERENCE.md).

## Configuration

The API-backed application reads these settings from its environment or local `.env` file. Keep credentials out of version control.

| Setting | Purpose |
| --- | --- |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Database name and credentials |
| `POSTGRES_HOST` | Database hostname, default `localhost` |
| `POSTGRES_PORT` | Database port, default `5432` |
| `POSTGRES_SSLMODE` | Optional TLS mode; use `verify-full` with an appropriate trusted CA for remote databases |
| `EMR_CORS_ORIGINS` | Explicit comma-separated HTTP(S) origins; unset allows the local Vite origins, empty disables cross-origin access |
| `VITE_API_BASE_URL` | Frontend API origin; unset uses `http://127.0.0.1:8000`, empty supports a same-origin proxy |
| `VITE_EMR_BROWSER` | Set to `1` to build the isolated browser application instead of the HTTP-backed application |

Use separate credentials and database instances for development, test and any hosted fictional application. The Compose database binds only to loopback. Apply Alembic migrations before starting a newly configured API. Hosting with HTTPS, restricted database networking and appropriate secret management is necessary but does not establish clinical readiness.

## Public workspace boundary

The public build reuses the FastAPI routes inside a Web Worker with a pinned Pyodide runtime and a per-tab SQLite database. Clinical requests stay within the browser. Accounts, sessions, records and audit history are isolated from other tabs; signing out does not erase edits. Reset, reload or closing the tab discards the database. Previously downloaded audit CSV files are not erased by reset.

The API logic still enforces role and ownership checks, but a person controlling their browser can modify the local application and its data. Browser roles are therefore illustrative, not a production security boundary. SQLite requests are serialized; PostgreSQL-specific locks and migration guarantees apply to the API-backed application, not the browser build. Use fictional data in both modes.

See [the audit](UX_AUDIT.md) for the verified implementation, release evidence and remaining risks.

## Resolving outstanding laboratory requests

The Pending Lab Requests worklist and the patient's Lab History section both provide direct actions to record a received result or cancel an outstanding request. Cancellation requires a reason and explicit confirmation; it retains the original order, cancellation timestamp and reason in the chart. Recording a result requires the collection date, result text and confirmation of the patient/result review. Neither action deletes records. A successful response removes the order from the pending queue; recording a result does not automatically release it to the patient portal. Finalized visits can still receive results or cancellation events under the existing API rules. Archived charts remain read-only. Staff can retain the pending request by dismissing the form without saving. The existing patient, encounter and order locking and authorization rules are unchanged.
