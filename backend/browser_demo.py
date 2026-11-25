"""Run the existing clinical API against a disposable, single-worker database."""

import asyncio
from datetime import date, datetime, time, timedelta, timezone
import json
import base64
import sys
from urllib.parse import unquote, urlsplit

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import (
    create_user_account, _create_user_account_with_hash, _PASSWORD_SCHEME, _PASSWORD_ITERATIONS,
)
from backend.diagnosis_indications import diagnosis_snapshot
from backend.models import (
    Allergy, Appointment, AppointmentStatusChange, Base, CareGoal,
    CareGoalProgress, Encounter, FollowUpTask, LabOrder, LabResult,
    Medication, MedicationIndication, LabOrderIndication, Patient, Problem, Referral, Vital,
)

BROWSER_PASSWORD = "Welcome-EMR-2026"


def create_browser_engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enforce_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    return engine


def _validated_demo_hashes(raw: str | None) -> dict[str, str] | None:
    """Accept only ephemeral, fixed demo identities, never a server credential."""
    if raw is None:
        return None
    if sys.platform != "emscripten":
        raise RuntimeError("Native demo seed hashes are browser-only")
    try:
        entries = json.loads(raw)
        if not isinstance(entries, dict) or set(entries) != {"admin", "clinician", "jordan.lee", "maria.thompson"}:
            return None
        salts = set()
        for value in entries.values():
            if not isinstance(value, str) or len(value) > 255:
                return None
            scheme, rounds, salt, digest = value.split("$")
            if scheme != _PASSWORD_SCHEME or int(rounds) != _PASSWORD_ITERATIONS:
                return None
            salt_bytes = base64.b64decode(salt, altchars=b"-_", validate=True)
            digest_bytes = base64.b64decode(digest, altchars=b"-_", validate=True)
            if len(salt_bytes) != 16 or len(digest_bytes) != 32:
                return None
            salts.add(salt_bytes)
        return entries if len(salts) == 4 else None
    except (ValueError, TypeError):
        return None


def seed_browser_database(engine: Engine, *, demo_hashes_json: str | None = None) -> None:
    """Create a reproducible starting chart, never use an external database."""
    if engine.dialect.name != "sqlite" or engine.url.database not in (None, "", ":memory:"):
        raise ValueError("Browser records require an in-memory SQLite database")
    demo_hashes = _validated_demo_hashes(demo_hashes_json)
    Base.metadata.create_all(engine)
    today = date.today()
    previous = today - timedelta(days=30)
    future = today + timedelta(days=30)
    past_time = datetime.combine(previous, time(10), tzinfo=timezone.utc)

    with Session(engine) as session:
        jordan = Patient(first_name="Jordan", last_name="Lee",
                         date_of_birth=date(1984, 3, 12), sex_at_birth="unknown",
                         pronouns="they/them")
        maria = Patient(first_name="Maria", last_name="Thompson",
                        date_of_birth=date(1957, 8, 24), sex_at_birth="female",
                        pronouns="she/her")
        devin = Patient(first_name="Devin", last_name="Brooks",
                        date_of_birth=date(2001, 11, 5), sex_at_birth="unknown")
        session.add_all([jordan, maria, devin])
        session.flush()
        def seed_account(username, **identity):
            if demo_hashes is None:
                return create_user_account(session, username=username, password=BROWSER_PASSWORD, **identity)
            return _create_user_account_with_hash(
                session, username=username, password_hash=demo_hashes[username], **identity,
            )

        for username, role in (("admin", "admin"), ("clinician", "clinician")):
            seed_account(username, account_type="staff", staff_role=role)
        for username, patient in (("jordan.lee", jordan), ("maria.thompson", maria)):
            seed_account(username, account_type="patient", patient_id=patient.id)

        hypertension = Problem(patient_id=jordan.id, name="Essential hypertension", status="active",
                               onset_date=today - timedelta(days=180), icd10_code="I10",
                               icd10_title="Essential (primary) hypertension", icd10_release="FY2027")
        lipids = Problem(patient_id=jordan.id, name="Hyperlipidemia", status="active",
                         onset_date=previous, icd10_code="E78.5",
                         icd10_title="Hyperlipidemia, unspecified", icd10_release="FY2027")
        screening = Problem(patient_id=jordan.id, name="Screening for blood disorders", status="resolved",
                            onset_date=previous, resolved_date=previous, icd10_code="Z13.0",
                            icd10_title="Encounter for screening for diseases of the blood and blood-forming organs and certain disorders involving the immune mechanism",
                            icd10_release="FY2027")
        session.add_all([hypertension, lipids, screening])
        session.flush()
        session.add_all([
            Medication(patient_id=jordan.id, name="Lisinopril", strength="20 mg",
                       dose="20 mg", route="oral", frequency="Daily", status="active",
                       start_date=previous, indications=[MedicationIndication(**diagnosis_snapshot(hypertension))]),
            Medication(patient_id=jordan.id, name="Atorvastatin", strength="20 mg",
                       dose="20 mg", route="oral", frequency="Nightly", status="active",
                       start_date=previous, indications=[MedicationIndication(**diagnosis_snapshot(lipids))]),
            Allergy(patient_id=maria.id, allergen="Penicillin", reaction="Rash",
                    severity="moderate", status="active"),
            Vital(patient_id=jordan.id, recorded_on=previous, systolic_bp=142,
                  diastolic_bp=88, heart_rate=76, weight_kg=84),
            Vital(patient_id=jordan.id, recorded_on=today - timedelta(days=2),
                  systolic_bp=132, diastolic_bp=82, heart_rate=72, weight_kg=83.5),
        ])

        visits = [
            Appointment(patient_id=jordan.id, scheduled_date=previous,
                        start_time=time(9), duration_minutes=30,
                        reason_for_visit="Annual physical", status="completed"),
            Appointment(patient_id=jordan.id, scheduled_date=today,
                        start_time=time(9, 30), duration_minutes=30,
                        reason_for_visit="Blood pressure follow-up", status="scheduled"),
            Appointment(patient_id=maria.id, scheduled_date=today,
                        start_time=time(10, 15), duration_minutes=30,
                        reason_for_visit="Medication review", status="scheduled"),
            Appointment(patient_id=jordan.id, scheduled_date=future,
                        start_time=time(10, 30), duration_minutes=30,
                        reason_for_visit="Follow-up visit", status="scheduled"),
        ]
        session.add_all(visits)
        session.flush()
        for appointment in visits:
            session.add(AppointmentStatusChange(
                appointment_id=appointment.id, previous_status=None, new_status="scheduled",
            ))
        for prior, current in (("scheduled", "checked_in"), ("checked_in", "completed")):
            session.add(AppointmentStatusChange(
                appointment_id=visits[0].id, previous_status=prior, new_status=current,
                changed_at=past_time,
            ))

        note = Encounter(
            patient_id=jordan.id, appointment_id=visits[0].id,
            visit_date=previous, reason_for_visit="Annual physical",
            subjective="Reports monitoring blood pressure at home.",
            objective="Reviewed vital signs and medication list.",
            assessment="Hypertension and hyperlipidemia reviewed.",
            plan="Continue current care plan and review interval readings.",
            patient_instructions="Bring your blood pressure log to your next visit.",
            finalized_at=past_time,
        )
        goal = CareGoal(patient_id=jordan.id, title="Review home blood pressure readings",
                        target_date=future, status="active", created_at=past_time)
        session.add_all([note, goal])
        session.flush()
        session.add_all([
            CareGoalProgress(goal_id=goal.id, note="Home readings reviewed.", recorded_at=past_time),
            FollowUpTask(patient_id=jordan.id, care_goal_id=goal.id,
                         title="Review home readings", due_date=today, status="open"),
            Referral(encounter_id=note.id, specialty="Nutrition counseling",
                     reason="Review dietary habits", priority="routine", status="requested",
                     requested_at=past_time),
        ])
        orders = [
            LabOrder(encounter_id=note.id, test_name="Lipid panel", priority="routine",
                     status="resulted", ordered_at=past_time,
                     indications=[LabOrderIndication(**diagnosis_snapshot(lipids))]),
            LabOrder(encounter_id=note.id, test_name="Basic metabolic panel", priority="routine",
                     status="ordered", ordered_at=past_time,
                     clinical_reason="Blood pressure medication monitoring", indications=[LabOrderIndication(**diagnosis_snapshot(hypertension))]),
            LabOrder(encounter_id=note.id, test_name="Complete blood count", priority="routine",
                     status="resulted", ordered_at=past_time,
                     clinical_reason="Routine screening for blood disorders", indications=[LabOrderIndication(**diagnosis_snapshot(screening))]),
        ]
        session.add_all(orders)
        session.flush()
        session.add_all([
            LabResult(lab_order_id=orders[0].id, collected_on=previous,
                      result_text="LDL 121 mg/dL; HDL 52 mg/dL.",
                      reported_at=past_time, released_at=past_time),
            LabResult(lab_order_id=orders[2].id, collected_on=previous,
                      result_text="Results recorded; awaiting review.", reported_at=past_time),
        ])
        session.commit()


async def dispatch(app, request: dict) -> dict:
    """Translate a browser message into an ASGI HTTP exchange without a socket."""
    url = urlsplit(request["url"])
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1", "method": request["method"], "scheme": "http",
        "path": unquote(url.path), "raw_path": url.path.encode("ascii"),
        "query_string": url.query.encode("ascii"), "root_path": "",
        "headers": [(key.lower().encode("latin-1"), value.encode("latin-1"))
                    for key, value in request.get("headers", [])],
        "server": ("emr.local", 80), "client": ("127.0.0.1", 0),
    }
    sent = False
    status = 500
    headers = []
    chunks = []

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": request.get("body", "").encode("utf-8"),
                    "more_body": False}
        # The request remains connected until the ASGI response finishes.
        await asyncio.Future()

    async def send(message):
        nonlocal status, headers
        if message["type"] == "http.response.start":
            status = message["status"]
            headers = [(key.decode("latin-1"), value.decode("latin-1"))
                       for key, value in message.get("headers", [])]
        elif message["type"] == "http.response.body":
            chunks.append(bytes(message.get("body", b"")))

    await app(scope, receive, send)
    return {"status": status, "headers": headers, "body": b"".join(chunks).decode("utf-8")}


def initialize_browser(demo_hashes_json: str | None = None) -> None:
    if sys.platform != "emscripten":
        raise RuntimeError("Browser initialization is not a server operation")

    # A secure browser context must supply freshly derived native hashes.
    # Reject missing/invalid inputs before creating any records. Never use a
    # weaker or non-native password implementation as a silent fallback.
    if _validated_demo_hashes(demo_hashes_json) is None:
        raise RuntimeError("Secure browser password initialization unavailable")

    # Requests are serialized by the dedicated worker. WASM has no native
    # thread pool, so synchronous handlers run in the worker itself.
    import anyio.to_thread

    async def run_sync(func, *args, **_):
        return func(*args)

    anyio.to_thread.run_sync = run_sync
    from backend.database import engine

    seed_browser_database(engine, demo_hashes_json=demo_hashes_json)


async def browser_request(raw: str) -> str:
    from backend.main import app

    return json.dumps(await dispatch(app, json.loads(raw)))
