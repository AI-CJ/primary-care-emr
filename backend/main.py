from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from starlette.routing import Match
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.database import engine
from backend.account_auth import authenticate_user
from backend.audit import record_audit_event
from backend.appointment_change_requests import (
    AppointmentChangeRequestCreate, AppointmentChangeRequestRead,
    StaffAppointmentChangeRequestRead, submit_appointment_change_request,
    list_patient_change_requests, list_pending_change_requests, review_change_request,
)
from backend.communication_preferences import (
    CommunicationPreferencesPayload, read_communication_preferences,
    replace_communication_preferences,
)
from backend.audit_review import (
    AuditActivitySummary, AuditEventRead, AuditEventType, export_audit_csv,
    list_audit_events, summarize_audit_activity,
)
from backend.session_auth import create_session, get_session_account, revoke_session
from backend.models import UserAccount
from backend.schemas import AuthAccountRead, AuthLoginRequest, AuthLoginResponse
from backend.patient_timeline import list_patient_timeline
from backend.portal_medications import list_portal_preview_medications
from backend.portal_problems import list_portal_preview_problems
from backend.portal_allergies import list_portal_preview_allergies
from backend.portal_vitals import list_portal_preview_vitals
from backend.portal_care_goals import list_portal_preview_care_goals
from backend.portal_appointments import list_portal_preview_appointments
from backend.care_goals import (
    complete_care_goal,
    create_care_goal,
    discontinue_care_goal,
    list_active_care_goals,
    list_care_goals,
    list_goal_progress,
    record_goal_progress,
)
from backend.follow_up_tasks import (
    cancel_follow_up_task,
    complete_follow_up_task,
    create_follow_up_task,
    list_open_follow_up_tasks,
    list_follow_up_tasks,
    list_follow_up_due_date_changes,
    reschedule_follow_up_task,
)
from backend.encounters import (
    apply_encounter_update,
    create_encounter,
    create_encounter_addendum,
    finalize_encounter,
    list_portal_preview_visits,
)
from backend.encounter_problems import (
    link_encounter_problem,
    list_encounter_problems,
    unlink_encounter_problem,
)
from backend.encounter_medications import (
    link_encounter_medication,
    list_encounter_medications,
    unlink_encounter_medication,
)
from backend.encounter_allergies import (
    link_encounter_allergy,
    list_encounter_allergies,
    unlink_encounter_allergy,
)
from backend.encounter_vitals import (
    link_encounter_vital,
    list_encounter_vitals,
    unlink_encounter_vital,
)
from backend.lab_orders import (
    cancel_lab_order,
    create_lab_order,
    list_lab_orders,
    list_patient_lab_orders,
    list_portal_preview_lab_orders,
    list_pending_lab_orders,
    list_unreleased_lab_results,
    read_lab_result,
    record_lab_result,
    release_lab_result,
)
from backend.referrals import (
    cancel_referral,
    complete_referral,
    create_referral,
    list_referrals,
    list_patient_referrals,
    list_portal_preview_referrals,
    list_pending_referrals,
)
from backend.scheduling import (
    cancel_appointment,
    check_in_appointment,
    complete_appointment,
    ensure_appointment_slot_open,
    list_daily_schedule,
    list_past_appointments,
    mark_appointment_no_show,
    record_appointment_status_change,
    reschedule_appointment,
)
from backend.models import (
    Allergy, Appointment, AppointmentStatusChange, Encounter,
    EncounterAddendum, Medication, Patient, Problem, Vital,
)
from backend.schemas import (
    AllergyCreate,
    ActiveCareGoalRead,
    CareGoalComplete,
    CareGoalCreate,
    CareGoalDiscontinue,
    CareGoalProgressCreate,
    CareGoalProgressRead,
    CareGoalRead,
    PortalCareGoalSummary,
    FollowUpTaskCancel,
    FollowUpTaskComplete,
    FollowUpTaskCreate,
    OpenFollowUpTaskRead,
    FollowUpTaskRead,
    FollowUpTaskReschedule,
    FollowUpDueDateChangeRead,
    EncounterAllergyLinkCreate,
    EncounterAllergyRead,
    AllergyRead,
    PortalAllergySummary,
    AppointmentCreate,
    AppointmentRead,
    PatientAppointmentRead,
    PortalAppointmentSummary,
    AppointmentStatusChangeRead,
    EncounterAddendumCreate,
    EncounterAddendumRead,
    EncounterMedicationLinkCreate,
    EncounterMedicationRead,
    EncounterProblemLinkCreate,
    EncounterProblemRead,
    EncounterVitalLinkCreate,
    EncounterVitalRead,
    EncounterCreate,
    EncounterRead,
    EncounterUpdate,
    PortalVisitSummary,
    LabOrderCancel,
    LabOrderCreate,
    LabOrderRead,
    LabResultCreate,
    LabResultRead,
    PatientLabOrderRead,
    PortalLabOrderSummary,
    PendingLabOrderRead,
    UnreleasedLabResultRead,
    ReferralCancel,
    ReferralComplete,
    ReferralCreate,
    ReferralRead,
    PatientReferralRead,
    PortalReferralSummary,
    PendingReferralRead,
    MedicationCreate,
    MedicationRead,
    PortalMedicationSummary,
    PortalProblemSummary,
    PortalVitalSummary,
    PatientCreate,
    PatientRead,
    PatientTimelineEntry,
    ProblemCreate,
    ProblemRead,
    ScheduleEntryRead,
    DailyScheduleEntryRead,
    SchedulePatientRead,
    VitalCreate,
    VitalRead,
)


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Invalid or missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    return credentials.credentials


def _current_account(request: Request, token: str = Depends(_bearer_token)) -> UserAccount:
    with Session(engine) as session:
        account = get_session_account(session, token)
        if account is None:
            raise _unauthorized()
        request.state.audit_actor_user_id = account.id
        request.state.audit_patient_id = account.patient_id
        return account


def _current_patient_account(account: UserAccount = Depends(_current_account)) -> UserAccount:
    if account.account_type != "patient" or account.patient_id is None:
        raise HTTPException(status_code=403, detail="Access denied")
    return account


# Clinical routes are staff-only; patient-facing routes must opt in explicitly.
# Keeping the check at the HTTP boundary also covers newly added routes.
_PUBLIC_PATHS = {"/", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
_AUTH_PATHS = {"/auth/login", "/auth/me", "/auth/logout"}
_PATIENT_GET_PATHS = {
    "/portal/appointments", "/portal/problems", "/portal/medications",
    "/portal/allergies", "/portal/vitals", "/portal/care-goals",
    "/portal/visits", "/portal/lab-orders", "/portal/referrals",
    "/portal/communication-preferences", "/portal/appointment-change-requests",
}
_PATIENT_WRITE_PATHS = {
    ("PUT", "/portal/communication-preferences"),
    ("POST", "/portal/appointment-change-requests"),
}


def _audit_clinical_access(request: Request, status_code: int) -> None:
    """Save a safe route template, never a raw URL, query, header or body."""
    route_template = "/unmatched"
    path_params = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        match, child_scope = route.matches(request.scope)
        if match is Match.FULL:
            route_template = route.path
            path_params = child_scope.get("path_params", {})
            break

    def numeric_id(name: str) -> int | None:
        # Starlette path parameters are strings unless a converter is declared.
        value = path_params.get(name)
        if isinstance(value, int):
            return value if 0 <= value <= 2_147_483_647 else None
        if isinstance(value, str) and value.isascii() and value.isdecimal():
            parsed = int(value) if len(value) <= 10 else None
            return parsed if parsed is not None and parsed <= 2_147_483_647 else None
        return None

    resource_id = next(
        (
            value for name in (
                "patient_id", "encounter_id", "goal_id", "task_id", "problem_id",
                "medication_id", "allergy_id", "vital_id", "order_id",
                "referral_id", "appointment_id", "request_id",
            )
            if (value := numeric_id(name)) is not None
        ),
        None,
    )
    subject_patient_id = getattr(request.state, "audit_patient_id", None)
    if subject_patient_id is None:
        subject_patient_id = numeric_id("patient_id")
    event_type = (
        "access_denied" if status_code in {401, 403}
        else "clinical_read" if request.method == "GET"
        else "clinical_write"
    )
    with Session(engine) as session:
        record_audit_event(
            session, event_type=event_type, route_template=route_template,
            http_method=request.method, status_code=status_code,
            actor_user_id=getattr(request.state, "audit_actor_user_id", None),
            subject_patient_id=subject_patient_id, resource_id=resource_id,
        )
        session.commit()


async def _run_clinical_endpoint(request: Request, call_next):
    """Persist failed clinical access attempts even when handlers raise."""
    try:
        return await call_next(request)
    except Exception:
        # Record only the templated route and status, never exception details.
        _audit_clinical_access(request, 500)
        raise


@app.middleware("http")
async def require_clinical_access(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path in _PUBLIC_PATHS:
        return await call_next(request)

    if request.url.path in _AUTH_PATHS:
        # Login and logout audit writes share the authentication transaction.
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    if ((request.method == "GET" and request.url.path in _PATIENT_GET_PATHS)
            or (request.method, request.url.path) in _PATIENT_WRITE_PATHS):
        # The patient-only dependency identifies the actor and enforces ownership.
        response = await _run_clinical_endpoint(request, call_next)
    else:
        scheme, separator, token = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not separator or not token:
            response = JSONResponse(
                {"detail": "Invalid or missing credentials"},
                status_code=401, headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            with Session(engine) as session:
                account = get_session_account(session, token)
                if account is not None:
                    request.state.audit_actor_user_id = account.id
                    request.state.audit_patient_id = account.patient_id
                staff_allowed = (
                    account is not None and account.account_type == "staff"
                    and account.staff_role in {"admin", "clinician"}
                )
            if account is None:
                response = JSONResponse(
                    {"detail": "Invalid or missing credentials"},
                    status_code=401, headers={"WWW-Authenticate": "Bearer"},
                )
            elif not staff_allowed:
                response = JSONResponse({"detail": "Access denied"}, status_code=403)
            else:
                response = await _run_clinical_endpoint(request, call_next)

    response.headers["Cache-Control"] = "no-store"
    _audit_clinical_access(request, response.status_code)
    return response


@app.post("/auth/login", response_model=AuthLoginResponse)
def login(credentials: AuthLoginRequest):
    with Session(engine) as session:
        account = authenticate_user(session, credentials.username, credentials.password)
        if account is None:
            # Never store a submitted username or password on failed authentication.
            record_audit_event(
                session, event_type="login_failure", route_template="/auth/login",
                http_method="POST", status_code=401,
            )
            session.commit()
            raise _unauthorized()
        token, record = create_session(session, account)
        record_audit_event(
            session, event_type="login_success", route_template="/auth/login",
            http_method="POST", status_code=200, actor_user_id=account.id,
            subject_patient_id=account.patient_id,
        )
        session.commit()
        return AuthLoginResponse(access_token=token, expires_at=record.expires_at)


@app.get("/auth/me", response_model=AuthAccountRead)
def read_current_account(account: UserAccount = Depends(_current_account)):
    return account


@app.post("/auth/logout", status_code=204)
def logout(token: str = Depends(_bearer_token)):
    with Session(engine) as session:
        account = get_session_account(session, token)
        if account is None:
            raise _unauthorized()
        revoke_session(session, token)
        record_audit_event(
            session, event_type="logout", route_template="/auth/logout",
            http_method="POST", status_code=204, actor_user_id=account.id,
            subject_patient_id=account.patient_id,
        )
        session.commit()


@app.get("/admin/audit-events", response_model=list[AuditEventRead])
def read_audit_events(
    limit: int = Query(default=50, ge=1, le=100),
    before_id: int | None = Query(default=None, ge=1),
    event_type: AuditEventType | None = None,
    account: UserAccount = Depends(_current_account),
):
    """Allow administrators, but not clinical staff or patients, to review audits."""
    if account.account_type != "staff" or account.staff_role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    with Session(engine) as session:
        return list_audit_events(
            session, limit=limit, before_id=before_id, event_type=event_type,
        )


@app.get("/admin/audit-events/activity", response_model=AuditActivitySummary)
def read_audit_activity(
    hours: int = Query(default=24, ge=1, le=168),
    account: UserAccount = Depends(_current_account),
):
    """Review recent failure counts without returning patient or account details."""
    if account.account_type != "staff" or account.staff_role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    with Session(engine) as session:
        return summarize_audit_activity(session, hours=hours)


@app.get("/admin/audit-events/export")
def download_audit_events(
    limit: int = Query(default=100, ge=1, le=100),
    before_id: int | None = Query(default=None, ge=1),
    event_type: AuditEventType | None = None,
    account: UserAccount = Depends(_current_account),
):
    """Export at most one page of approved audit metadata for administrators."""
    if account.account_type != "staff" or account.staff_role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    with Session(engine) as session:
        content = export_audit_csv(list_audit_events(
            session, limit=limit, before_id=before_id, event_type=event_type,
        ))
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="audit-events.csv"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/")
def read_root():
    return {"message": "Primary Care EMR API"}


@app.get(
    "/patients",
    response_model=list[PatientRead],
)
def read_patients(search: str | None = None):
    query = select(Patient)

    if search and search.strip():
        search_term = f"%{search.strip()}%"

        query = query.where(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.preferred_name.ilike(search_term),
                Patient.middle_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
            )
        )

    query = query.order_by(
        Patient.last_name,
        Patient.first_name,
        Patient.date_of_birth,
    )

    with Session(engine) as session:
        patients = session.scalars(query).all()
        return list(patients)


@app.post(
    "/patients",
    response_model=PatientRead,
    status_code=201,
)
def create_patient(patient_data: PatientCreate):
    patient = Patient(**patient_data.model_dump())

    with Session(engine) as session:
        session.add(patient)
        session.commit()
        session.refresh(patient)
        return patient


@app.put(
    "/patients/{patient_id}",
    response_model=PatientRead,
)
def update_patient(
    patient_id: int,
    patient_data: PatientCreate,
):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        for field, value in patient_data.model_dump().items():
            setattr(patient, field, value)

        session.commit()
        session.refresh(patient)
        return patient


@app.get(
    "/patients/{patient_id}",
    response_model=PatientRead,
)
def read_patient(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        return patient


@app.get(
    "/patients/{patient_id}/timeline",
    response_model=list[PatientTimelineEntry],
)
def read_patient_timeline(patient_id: int, limit: int = Query(default=50, ge=1, le=200)):
    with Session(engine) as session:
        return list_patient_timeline(session, patient_id, limit=limit)


@app.get(
    "/worklists/active-care-goals",
    response_model=list[ActiveCareGoalRead],
)
def read_active_care_goals():
    today = date.today()
    with Session(engine) as session:
        return [
            ActiveCareGoalRead(
                **CareGoalRead.model_validate(goal).model_dump(),
                patient_name=f"{patient.preferred_name or patient.first_name} {patient.last_name}",
                is_overdue=goal.target_date is not None and goal.target_date < today,
            )
            for goal, patient in list_active_care_goals(session)
        ]


@app.get(
    "/patients/{patient_id}/portal-preview/care-goals",
    response_model=list[PortalCareGoalSummary],
)
def read_portal_preview_care_goals(patient_id: int):
    with Session(engine) as session:
        return list_portal_preview_care_goals(session, patient_id)


@app.get("/portal/care-goals", response_model=list[PortalCareGoalSummary])
def read_portal_care_goals(account: UserAccount = Depends(_current_patient_account)):
    with Session(engine) as session:
        return list_portal_preview_care_goals(session, account.patient_id)


@app.get(
    "/patients/{patient_id}/care-goals",
    response_model=list[CareGoalRead],
)
def read_patient_care_goals(patient_id: int):
    with Session(engine) as session:
        return list_care_goals(session, patient_id)


@app.post(
    "/patients/{patient_id}/care-goals",
    response_model=CareGoalRead,
    status_code=201,
)
def add_patient_care_goal(patient_id: int, goal_data: CareGoalCreate):
    with Session(engine) as session:
        goal = create_care_goal(session, patient_id, goal_data)
        session.commit()
        session.refresh(goal)
        return goal


@app.post(
    "/care-goals/{goal_id}/complete",
    response_model=CareGoalRead,
)
def complete_patient_care_goal(goal_id: int, completion: CareGoalComplete):
    with Session(engine) as session:
        goal = complete_care_goal(session, goal_id, completion)
        session.commit()
        session.refresh(goal)
        return goal


@app.post(
    "/care-goals/{goal_id}/discontinue",
    response_model=CareGoalRead,
)
def discontinue_patient_care_goal(goal_id: int, discontinuation: CareGoalDiscontinue):
    with Session(engine) as session:
        goal = discontinue_care_goal(session, goal_id, discontinuation)
        session.commit()
        session.refresh(goal)
        return goal


@app.get(
    "/care-goals/{goal_id}/progress",
    response_model=list[CareGoalProgressRead],
)
def read_care_goal_progress(goal_id: int):
    with Session(engine) as session:
        return list_goal_progress(session, goal_id)


@app.post(
    "/care-goals/{goal_id}/progress",
    response_model=CareGoalProgressRead,
    status_code=201,
)
def add_care_goal_progress(goal_id: int, progress_data: CareGoalProgressCreate):
    with Session(engine) as session:
        entry = record_goal_progress(session, goal_id, progress_data)
        session.commit()
        session.refresh(entry)
        return entry


@app.get(
    "/worklists/open-follow-up-tasks",
    response_model=list[OpenFollowUpTaskRead],
)
def read_open_follow_up_tasks():
    today = date.today()
    with Session(engine) as session:
        return [
            OpenFollowUpTaskRead(
                **FollowUpTaskRead.model_validate(task).model_dump(),
                patient_name=f"{patient.preferred_name or patient.first_name} {patient.last_name}",
                is_overdue=task.due_date is not None and task.due_date < today,
            )
            for task, patient in list_open_follow_up_tasks(session)
        ]


@app.get(
    "/patients/{patient_id}/follow-up-tasks",
    response_model=list[FollowUpTaskRead],
)
def read_patient_follow_up_tasks(patient_id: int):
    with Session(engine) as session:
        return list_follow_up_tasks(session, patient_id)


@app.post(
    "/patients/{patient_id}/follow-up-tasks",
    response_model=FollowUpTaskRead,
    status_code=201,
)
def add_patient_follow_up_task(patient_id: int, task_data: FollowUpTaskCreate):
    with Session(engine) as session:
        task = create_follow_up_task(session, patient_id, task_data)
        session.commit()
        session.refresh(task)
        return task


@app.post(
    "/follow-up-tasks/{task_id}/complete",
    response_model=FollowUpTaskRead,
)
def complete_patient_follow_up_task(task_id: int, completion: FollowUpTaskComplete):
    with Session(engine) as session:
        task = complete_follow_up_task(session, task_id, completion)
        session.commit()
        session.refresh(task)
        return task


@app.post(
    "/follow-up-tasks/{task_id}/cancel",
    response_model=FollowUpTaskRead,
)
def cancel_patient_follow_up_task(task_id: int, cancellation: FollowUpTaskCancel):
    with Session(engine) as session:
        task = cancel_follow_up_task(session, task_id, cancellation)
        session.commit()
        session.refresh(task)
        return task


@app.post(
    "/follow-up-tasks/{task_id}/reschedule",
    response_model=FollowUpTaskRead,
)
def reschedule_patient_follow_up_task(task_id: int, change: FollowUpTaskReschedule):
    with Session(engine) as session:
        task = reschedule_follow_up_task(session, task_id, change)
        session.commit()
        session.refresh(task)
        return task


@app.get(
    "/follow-up-tasks/{task_id}/due-date-changes",
    response_model=list[FollowUpDueDateChangeRead],
)
def read_follow_up_due_date_changes(task_id: int):
    with Session(engine) as session:
        return list_follow_up_due_date_changes(session, task_id)


@app.get(
    "/patients/{patient_id}/problems",
    response_model=list[ProblemRead],
)
def read_patient_problems(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        query = (
            select(Problem)
            .where(Problem.patient_id == patient_id)
            .order_by(Problem.status, Problem.name)
        )

        problems = session.scalars(query).all()
        return list(problems)


@app.get(
    "/patients/{patient_id}/portal-preview/problems",
    response_model=list[PortalProblemSummary],
)
def read_portal_preview_problems(patient_id: int):
    with Session(engine) as session:
        return list_portal_preview_problems(session, patient_id)


@app.get("/portal/problems", response_model=list[PortalProblemSummary])
def read_portal_problems(account: UserAccount = Depends(_current_patient_account)):
    # The signed-in account supplies the patient ID, never a request parameter.
    with Session(engine) as session:
        return list_portal_preview_problems(session, account.patient_id)


@app.post(
    "/patients/{patient_id}/problems",
    response_model=ProblemRead,
    status_code=201,
)
def create_patient_problem(
    patient_id: int,
    problem_data: ProblemCreate,
):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        problem = Problem(
            patient_id=patient_id,
            **problem_data.model_dump(),
        )

        session.add(problem)
        session.commit()
        session.refresh(problem)
        return problem


@app.put(
    "/problems/{problem_id}",
    response_model=ProblemRead,
)
def update_problem(
    problem_id: int,
    problem_data: ProblemCreate,
):
    with Session(engine) as session:
        problem = session.get(Problem, problem_id)

        if problem is None:
            raise HTTPException(
                status_code=404,
                detail="Problem not found",
            )

        for field, value in problem_data.model_dump().items():
            setattr(problem, field, value)

        session.commit()
        session.refresh(problem)
        return problem


@app.get(
    "/patients/{patient_id}/medications",
    response_model=list[MedicationRead],
)
def read_patient_medications(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        query = (
            select(Medication)
            .where(Medication.patient_id == patient_id)
            .order_by(Medication.status, Medication.name)
        )

        medications = session.scalars(query).all()
        return list(medications)


@app.get(
    "/patients/{patient_id}/portal-preview/medications",
    response_model=list[PortalMedicationSummary],
)
def read_portal_preview_medications(patient_id: int):
    with Session(engine) as session:
        return list_portal_preview_medications(session, patient_id)


@app.get("/portal/medications", response_model=list[PortalMedicationSummary])
def read_portal_medications(account: UserAccount = Depends(_current_patient_account)):
    # Only the authenticated account identifies the patient.
    with Session(engine) as session:
        return list_portal_preview_medications(session, account.patient_id)


@app.post(
    "/patients/{patient_id}/medications",
    response_model=MedicationRead,
    status_code=201,
)
def create_patient_medication(
    patient_id: int,
    medication_data: MedicationCreate,
):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        medication = Medication(
            patient_id=patient_id,
            **medication_data.model_dump(),
        )

        session.add(medication)
        session.commit()
        session.refresh(medication)
        return medication


@app.put(
    "/medications/{medication_id}",
    response_model=MedicationRead,
)
def update_medication(
    medication_id: int,
    medication_data: MedicationCreate,
):
    with Session(engine) as session:
        medication = session.get(Medication, medication_id)

        if medication is None:
            raise HTTPException(
                status_code=404,
                detail="Medication not found",
            )

        for field, value in medication_data.model_dump().items():
            setattr(medication, field, value)

        session.commit()
        session.refresh(medication)
        return medication


@app.get(
    "/patients/{patient_id}/allergies",
    response_model=list[AllergyRead],
)
def read_patient_allergies(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        query = (
            select(Allergy)
            .where(Allergy.patient_id == patient_id)
            .order_by(Allergy.status, Allergy.allergen)
        )

        allergies = session.scalars(query).all()
        return list(allergies)


@app.get(
    "/patients/{patient_id}/portal-preview/allergies",
    response_model=list[PortalAllergySummary],
)
def read_portal_preview_allergies(patient_id: int):
    with Session(engine) as session:
        return list_portal_preview_allergies(session, patient_id)


@app.get("/portal/allergies", response_model=list[PortalAllergySummary])
def read_portal_allergies(account: UserAccount = Depends(_current_patient_account)):
    with Session(engine) as session:
        return list_portal_preview_allergies(session, account.patient_id)


@app.post(
    "/patients/{patient_id}/allergies",
    response_model=AllergyRead,
    status_code=201,
)
def create_patient_allergy(
    patient_id: int,
    allergy_data: AllergyCreate,
):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        allergy = Allergy(
            patient_id=patient_id,
            **allergy_data.model_dump(),
        )

        session.add(allergy)
        session.commit()
        session.refresh(allergy)
        return allergy


@app.put(
    "/allergies/{allergy_id}",
    response_model=AllergyRead,
)
def update_allergy(
    allergy_id: int,
    allergy_data: AllergyCreate,
):
    with Session(engine) as session:
        allergy = session.get(Allergy, allergy_id)

        if allergy is None:
            raise HTTPException(
                status_code=404,
                detail="Allergy not found",
            )

        for field, value in allergy_data.model_dump().items():
            setattr(allergy, field, value)

        session.commit()
        session.refresh(allergy)
        return allergy


@app.get(
    "/patients/{patient_id}/portal-preview/vitals",
    response_model=list[PortalVitalSummary],
)
def read_portal_preview_vitals(patient_id: int):
    with Session(engine) as session:
        return list_portal_preview_vitals(session, patient_id)


@app.get("/portal/vitals", response_model=list[PortalVitalSummary])
def read_portal_vitals(account: UserAccount = Depends(_current_patient_account)):
    # Return only recent measurements for the patient linked to this session.
    with Session(engine) as session:
        return list_portal_preview_vitals(session, account.patient_id)


@app.get(
    "/patients/{patient_id}/vitals",
    response_model=list[VitalRead],
)
def read_patient_vitals(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        query = (
            select(Vital)
            .where(Vital.patient_id == patient_id)
            .order_by(Vital.recorded_on.desc(), Vital.id.desc())
        )
        return list(session.scalars(query).all())


@app.post(
    "/patients/{patient_id}/vitals",
    response_model=VitalRead,
    status_code=201,
)
def create_patient_vital(patient_id: int, vital_data: VitalCreate):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        vital = Vital(patient_id=patient_id, **vital_data.model_dump())
        session.add(vital)
        session.commit()
        session.refresh(vital)
        return vital


@app.put(
    "/vitals/{vital_id}",
    response_model=VitalRead,
)
def update_vital(vital_id: int, vital_data: VitalCreate):
    with Session(engine) as session:
        vital = session.get(Vital, vital_id)
        if vital is None:
            raise HTTPException(status_code=404, detail="Vitals record not found")

        for field, value in vital_data.model_dump().items():
            setattr(vital, field, value)
        session.commit()
        session.refresh(vital)
        return vital


@app.get(
    "/patients/{patient_id}/encounters",
    response_model=list[EncounterRead],
)
def read_patient_encounters(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        query = (
            select(Encounter)
            .where(Encounter.patient_id == patient_id)
            .order_by(Encounter.visit_date.desc(), Encounter.id.desc())
        )
        return list(session.scalars(query).all())


@app.get(
    "/patients/{patient_id}/portal-preview/visits",
    response_model=list[PortalVisitSummary],
)
def read_portal_preview_visits(patient_id: int):
    with Session(engine) as session:
        return list_portal_preview_visits(session, patient_id)


@app.get("/portal/visits", response_model=list[PortalVisitSummary])
def read_portal_visits(account: UserAccount = Depends(_current_patient_account)):
    with Session(engine) as session:
        return list_portal_preview_visits(session, account.patient_id)


@app.post(
    "/patients/{patient_id}/encounters",
    response_model=EncounterRead,
    status_code=201,
)
def create_patient_encounter(
    patient_id: int,
    encounter_data: EncounterCreate,
):
    with Session(engine) as session:
        encounter = create_encounter(session, patient_id, encounter_data)
        session.commit()
        session.refresh(encounter)
        return encounter


@app.put(
    "/encounters/{encounter_id}",
    response_model=EncounterRead,
)
def update_encounter(
    encounter_id: int,
    encounter_data: EncounterUpdate,
):
    with Session(engine) as session:
        encounter = apply_encounter_update(session, encounter_id, encounter_data)
        session.commit()
        session.refresh(encounter)
        return encounter


@app.post(
    "/encounters/{encounter_id}/finalize",
    response_model=EncounterRead,
)
def finalize_patient_encounter(encounter_id: int):
    with Session(engine) as session:
        encounter = finalize_encounter(session, encounter_id)
        session.commit()
        session.refresh(encounter)
        return encounter


@app.get(
    "/encounters/{encounter_id}/addenda",
    response_model=list[EncounterAddendumRead],
)
def read_encounter_addenda(encounter_id: int):
    with Session(engine) as session:
        if session.get(Encounter, encounter_id) is None:
            raise HTTPException(status_code=404, detail="Visit note not found")

        query = (
            select(EncounterAddendum)
            .where(EncounterAddendum.encounter_id == encounter_id)
            .order_by(EncounterAddendum.created_at, EncounterAddendum.id)
        )
        return list(session.scalars(query).all())


@app.post(
    "/encounters/{encounter_id}/addenda",
    response_model=EncounterAddendumRead,
    status_code=201,
)
def add_encounter_addendum(
    encounter_id: int, addendum_data: EncounterAddendumCreate
):
    with Session(engine) as session:
        addendum = create_encounter_addendum(
            session, encounter_id, addendum_data
        )
        session.commit()
        session.refresh(addendum)
        return addendum


@app.get(
    "/encounters/{encounter_id}/problems",
    response_model=list[EncounterProblemRead],
)
def read_encounter_problems(encounter_id: int):
    with Session(engine) as session:
        return list_encounter_problems(session, encounter_id)


@app.post(
    "/encounters/{encounter_id}/problems",
    response_model=EncounterProblemRead,
    status_code=201,
)
def add_encounter_problem(
    encounter_id: int, link_data: EncounterProblemLinkCreate
):
    with Session(engine) as session:
        link = link_encounter_problem(session, encounter_id, link_data)
        session.commit()
        session.refresh(link)
        return link


@app.delete("/encounters/{encounter_id}/problems/{problem_id}", status_code=204)
def remove_encounter_problem(encounter_id: int, problem_id: int):
    with Session(engine) as session:
        unlink_encounter_problem(session, encounter_id, problem_id)
        session.commit()


@app.get(
    "/encounters/{encounter_id}/vitals",
    response_model=list[EncounterVitalRead],
)
def read_encounter_vitals(encounter_id: int):
    with Session(engine) as session:
        return list_encounter_vitals(session, encounter_id)


@app.post(
    "/encounters/{encounter_id}/vitals",
    response_model=EncounterVitalRead,
    status_code=201,
)
def add_encounter_vital(
    encounter_id: int, link_data: EncounterVitalLinkCreate
):
    with Session(engine) as session:
        link = link_encounter_vital(session, encounter_id, link_data)
        session.commit()
        session.refresh(link)
        return link


@app.delete("/encounters/{encounter_id}/vitals/{vital_id}", status_code=204)
def remove_encounter_vital(encounter_id: int, vital_id: int):
    with Session(engine) as session:
        unlink_encounter_vital(session, encounter_id, vital_id)
        session.commit()



@app.get(
    "/encounters/{encounter_id}/medications",
    response_model=list[EncounterMedicationRead],
)
def read_encounter_medications(encounter_id: int):
    with Session(engine) as session:
        return list_encounter_medications(session, encounter_id)


@app.post(
    "/encounters/{encounter_id}/medications",
    response_model=EncounterMedicationRead,
    status_code=201,
)
def add_encounter_medication(
    encounter_id: int, link_data: EncounterMedicationLinkCreate
):
    with Session(engine) as session:
        link = link_encounter_medication(session, encounter_id, link_data)
        session.commit()
        session.refresh(link)
        return link


@app.delete("/encounters/{encounter_id}/medications/{medication_id}", status_code=204)
def remove_encounter_medication(encounter_id: int, medication_id: int):
    with Session(engine) as session:
        unlink_encounter_medication(session, encounter_id, medication_id)
        session.commit()


@app.get(
    "/encounters/{encounter_id}/allergies",
    response_model=list[EncounterAllergyRead],
)
def read_encounter_allergies(encounter_id: int):
    with Session(engine) as session:
        return list_encounter_allergies(session, encounter_id)


@app.post(
    "/encounters/{encounter_id}/allergies",
    response_model=EncounterAllergyRead,
    status_code=201,
)
def add_encounter_allergy(encounter_id: int, link_data: EncounterAllergyLinkCreate):
    with Session(engine) as session:
        link = link_encounter_allergy(session, encounter_id, link_data)
        session.commit()
        session.refresh(link)
        return link


@app.delete("/encounters/{encounter_id}/allergies/{allergy_id}", status_code=204)
def remove_encounter_allergy(encounter_id: int, allergy_id: int):
    with Session(engine) as session:
        unlink_encounter_allergy(session, encounter_id, allergy_id)
        session.commit()



@app.get(
    "/worklists/pending-lab-orders",
    response_model=list[PendingLabOrderRead],
)
def read_pending_lab_orders():
    with Session(engine) as session:
        return [
            PendingLabOrderRead(
                **LabOrderRead.model_validate(order).model_dump(),
                patient_id=patient.id,
                patient_name=f"{patient.preferred_name or patient.first_name} {patient.last_name}",
                visit_date=visit_date,
            )
            for order, visit_date, patient in list_pending_lab_orders(session)
        ]


@app.get(
    "/worklists/unreleased-lab-results",
    response_model=list[UnreleasedLabResultRead],
)
def read_unreleased_lab_results():
    with Session(engine) as session:
        return [
            UnreleasedLabResultRead(
                order_id=order.id,
                patient_id=patient.id,
                patient_name=f"{patient.preferred_name or patient.first_name} {patient.last_name}",
                test_name=order.test_name,
                priority=order.priority,
                visit_date=visit_date,
                ordered_at=order.ordered_at,
                reported_at=reported_at,
            )
            for order, reported_at, visit_date, patient in list_unreleased_lab_results(session)
        ]


@app.get(
    "/patients/{patient_id}/portal-preview/lab-orders",
    response_model=list[PortalLabOrderSummary],
)
def read_portal_preview_lab_orders(patient_id: int):
    with Session(engine) as session:
        return list_portal_preview_lab_orders(session, patient_id)


@app.get("/portal/lab-orders", response_model=list[PortalLabOrderSummary])
def read_portal_lab_orders(account: UserAccount = Depends(_current_patient_account)):
    with Session(engine) as session:
        return list_portal_preview_lab_orders(session, account.patient_id)


@app.get(
    "/patients/{patient_id}/lab-orders",
    response_model=list[PatientLabOrderRead],
)
def read_patient_lab_orders(patient_id: int):
    with Session(engine) as session:
        return [
            PatientLabOrderRead(
                **LabOrderRead.model_validate(order).model_dump(),
                visit_date=visit_date,
                result=LabResultRead.model_validate(result) if result else None,
            )
            for order, visit_date, result in list_patient_lab_orders(session, patient_id)
        ]


@app.get(
    "/encounters/{encounter_id}/lab-orders",
    response_model=list[LabOrderRead],
)
def read_encounter_lab_orders(encounter_id: int):
    with Session(engine) as session:
        return list_lab_orders(session, encounter_id)


@app.post(
    "/encounters/{encounter_id}/lab-orders",
    response_model=LabOrderRead,
    status_code=201,
)
def add_encounter_lab_order(encounter_id: int, order_data: LabOrderCreate):
    with Session(engine) as session:
        order = create_lab_order(session, encounter_id, order_data)
        session.commit()
        session.refresh(order)
        return order


@app.post(
    "/lab-orders/{order_id}/cancel",
    response_model=LabOrderRead,
)
def cancel_order_request(order_id: int, cancellation: LabOrderCancel):
    with Session(engine) as session:
        order = cancel_lab_order(session, order_id, cancellation)
        session.commit()
        session.refresh(order)
        return order


@app.get(
    "/lab-orders/{order_id}/result",
    response_model=LabResultRead,
)
def read_order_result(order_id: int):
    with Session(engine) as session:
        return read_lab_result(session, order_id)


@app.post(
    "/lab-orders/{order_id}/result",
    response_model=LabResultRead,
    status_code=201,
)
def add_order_result(order_id: int, result_data: LabResultCreate):
    with Session(engine) as session:
        result = record_lab_result(session, order_id, result_data)
        session.commit()
        session.refresh(result)
        return result


@app.post(
    "/lab-orders/{order_id}/result/release",
    response_model=LabResultRead,
)
def release_order_result(order_id: int):
    with Session(engine) as session:
        result = release_lab_result(session, order_id)
        session.commit()
        session.refresh(result)
        return result


@app.get(
    "/worklists/pending-referrals",
    response_model=list[PendingReferralRead],
)
def read_pending_referrals():
    with Session(engine) as session:
        return [
            PendingReferralRead(
                **ReferralRead.model_validate(referral).model_dump(),
                patient_id=patient.id,
                patient_name=f"{patient.preferred_name or patient.first_name} {patient.last_name}",
                visit_date=visit_date,
            )
            for referral, visit_date, patient in list_pending_referrals(session)
        ]


@app.get(
    "/patients/{patient_id}/portal-preview/referrals",
    response_model=list[PortalReferralSummary],
)
def read_portal_preview_referrals(patient_id: int):
    with Session(engine) as session:
        return list_portal_preview_referrals(session, patient_id)


@app.get("/portal/referrals", response_model=list[PortalReferralSummary])
def read_portal_referrals(account: UserAccount = Depends(_current_patient_account)):
    with Session(engine) as session:
        return list_portal_preview_referrals(session, account.patient_id)


@app.get(
    "/patients/{patient_id}/referrals",
    response_model=list[PatientReferralRead],
)
def read_patient_referrals(patient_id: int):
    with Session(engine) as session:
        return [
            PatientReferralRead(
                **ReferralRead.model_validate(referral).model_dump(),
                visit_date=visit_date,
            )
            for referral, visit_date in list_patient_referrals(session, patient_id)
        ]


@app.get(
    "/encounters/{encounter_id}/referrals",
    response_model=list[ReferralRead],
)
def read_encounter_referrals(encounter_id: int):
    with Session(engine) as session:
        return list_referrals(session, encounter_id)


@app.post(
    "/encounters/{encounter_id}/referrals",
    response_model=ReferralRead,
    status_code=201,
)
def add_encounter_referral(encounter_id: int, referral_data: ReferralCreate):
    with Session(engine) as session:
        referral = create_referral(session, encounter_id, referral_data)
        session.commit()
        session.refresh(referral)
        return referral


@app.post(
    "/referrals/{referral_id}/cancel",
    response_model=ReferralRead,
)
def cancel_referral_request(referral_id: int, cancellation: ReferralCancel):
    with Session(engine) as session:
        referral = cancel_referral(session, referral_id, cancellation)
        session.commit()
        session.refresh(referral)
        return referral


@app.post(
    "/referrals/{referral_id}/complete",
    response_model=ReferralRead,
)
def complete_referral_request(referral_id: int, follow_up: ReferralComplete):
    with Session(engine) as session:
        referral = complete_referral(session, referral_id, follow_up)
        session.commit()
        session.refresh(referral)
        return referral


@app.get(
    "/schedule",
    response_model=list[DailyScheduleEntryRead],
)
def read_daily_schedule(day: date):
    """Read all appointments for a clinic-local day."""
    with Session(engine) as session:
        entries = list_daily_schedule(session, day)
        linked_notes = dict(session.execute(
            select(Encounter.appointment_id, Encounter.id)
            .join(Appointment, Appointment.id == Encounter.appointment_id)
            .where(
                Appointment.scheduled_date == day,
                Encounter.patient_id == Appointment.patient_id,
            )
        ).all())
        return [
            DailyScheduleEntryRead(
                appointment=PatientAppointmentRead(
                    **AppointmentRead.model_validate(appointment).model_dump(),
                    visit_note_id=linked_notes.get(appointment.id),
                ),
                patient=SchedulePatientRead.model_validate(patient),
            )
            for appointment, patient in entries
        ]



@app.get(
    "/worklists/past-appointments",
    response_model=list[DailyScheduleEntryRead],
)
def read_past_appointments(before: date):
    """List earlier visits whose appointment status has not been resolved."""
    with Session(engine) as session:
        entries = list_past_appointments(session, before)
        appointment_ids = [appointment.id for appointment, _ in entries]
        linked_notes = dict(session.execute(
            select(Encounter.appointment_id, Encounter.id)
            .join(Appointment, Appointment.id == Encounter.appointment_id)
            .where(
                Appointment.id.in_(appointment_ids),
                Encounter.patient_id == Appointment.patient_id,
            )
        ).all())
        return [
            DailyScheduleEntryRead(
                appointment=PatientAppointmentRead(
                    **AppointmentRead.model_validate(appointment).model_dump(),
                    visit_note_id=linked_notes.get(appointment.id),
                ),
                patient=SchedulePatientRead.model_validate(patient),
            )
            for appointment, patient in entries
        ]


@app.get(
    "/patients/{patient_id}/portal-preview/appointments",
    response_model=list[PortalAppointmentSummary],
)
def read_portal_preview_appointments(patient_id: int):
    with Session(engine) as session:
        return list_portal_preview_appointments(session, patient_id)


@app.get("/portal/communication-preferences", response_model=CommunicationPreferencesPayload)
def get_my_communication_preferences(
    account: UserAccount = Depends(_current_patient_account),
):
    """Read defaults without creating a database row until the patient saves."""
    with Session(engine) as session:
        return read_communication_preferences(session, account.patient_id)


@app.put("/portal/communication-preferences", response_model=CommunicationPreferencesPayload)
def update_my_communication_preferences(
    preferences: CommunicationPreferencesPayload,
    account: UserAccount = Depends(_current_patient_account),
):
    """Only replace the authenticated patient's choices, not clinical data."""
    with Session(engine) as session:
        return replace_communication_preferences(session, account.patient_id, preferences)


@app.get("/portal/appointment-change-requests",
         response_model=list[AppointmentChangeRequestRead])
def read_my_appointment_change_requests(
    account: UserAccount = Depends(_current_patient_account),
):
    with Session(engine) as session:
        return list_patient_change_requests(session, account.patient_id)


@app.post("/portal/appointment-change-requests", status_code=201,
          response_model=AppointmentChangeRequestRead)
def create_my_appointment_change_request(
    payload: AppointmentChangeRequestCreate,
    account: UserAccount = Depends(_current_patient_account),
):
    with Session(engine) as session:
        return submit_appointment_change_request(session, account.patient_id, payload)


@app.get("/worklists/appointment-change-requests",
         response_model=list[StaffAppointmentChangeRequestRead])
def read_pending_appointment_change_requests():
    with Session(engine) as session:
        return list_pending_change_requests(session)


@app.post("/appointment-change-requests/{request_id}/review",
          response_model=StaffAppointmentChangeRequestRead)
def mark_appointment_change_request_reviewed(request_id: int):
    # Review alone cannot change the visit's status or appointment time.
    with Session(engine) as session:
        return review_change_request(session, request_id)


@app.get("/portal/appointments", response_model=list[PortalAppointmentSummary])
def read_portal_appointments(account: UserAccount = Depends(_current_patient_account)):
    # Never accept the patient ID from the URL or query parameters.
    with Session(engine) as session:
        return list_portal_preview_appointments(session, account.patient_id)


@app.get(
    "/patients/{patient_id}/appointments",
    response_model=list[PatientAppointmentRead],
)
def read_patient_appointments(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        query = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(
                Appointment.scheduled_date.desc(),
                Appointment.start_time.desc(),
                Appointment.id.desc(),
            )
        )
        appointments = list(session.scalars(query).all())
        linked_notes = dict(session.execute(
            select(Encounter.appointment_id, Encounter.id)
            .where(
                Encounter.patient_id == patient_id,
                Encounter.appointment_id.is_not(None),
            )
        ).all())
        return [
            PatientAppointmentRead(
                **AppointmentRead.model_validate(appointment).model_dump(),
                visit_note_id=linked_notes.get(appointment.id),
            )
            for appointment in appointments
        ]


@app.post(
    "/patients/{patient_id}/appointments",
    response_model=AppointmentRead,
    status_code=201,
)
def create_patient_appointment(
    patient_id: int,
    appointment_data: AppointmentCreate,
):
    with Session(engine) as session:
        # Serialize scheduling changes for this patient before checking the slot.
        patient = session.scalar(
            select(Patient).where(Patient.id == patient_id).with_for_update()
        )
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        if appointment_data.status != "scheduled":
            raise HTTPException(
                status_code=409,
                detail="New appointments must be scheduled. Use appointment actions to change status.",
            )

        ensure_appointment_slot_open(session, patient_id, appointment_data)

        appointment = Appointment(
            patient_id=patient_id, **appointment_data.model_dump()
        )
        session.add(appointment)
        session.flush()
        record_appointment_status_change(session, appointment, None)
        session.commit()
        session.refresh(appointment)
        return appointment


@app.put(
    "/appointments/{appointment_id}",
    response_model=AppointmentRead,
)
def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentCreate,
):
    with Session(engine) as session:
        appointment = reschedule_appointment(
            session, appointment_id, appointment_data
        )
        session.commit()
        session.refresh(appointment)
        return appointment


@app.post(
    "/appointments/{appointment_id}/check-in",
    response_model=AppointmentRead,
)
def check_in_patient_appointment(appointment_id: int):
    with Session(engine) as session:
        appointment = check_in_appointment(session, appointment_id)
        session.commit()
        session.refresh(appointment)
        return appointment

@app.post(
    "/appointments/{appointment_id}/complete",
    response_model=AppointmentRead,
)
def complete_patient_appointment(appointment_id: int):
    with Session(engine) as session:
        appointment = complete_appointment(session, appointment_id)
        session.commit()
        session.refresh(appointment)
        return appointment


@app.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentRead,
)
def cancel_patient_appointment(appointment_id: int):
    with Session(engine) as session:
        appointment = cancel_appointment(session, appointment_id)
        session.commit()
        session.refresh(appointment)
        return appointment


@app.post(
    "/appointments/{appointment_id}/no-show",
    response_model=AppointmentRead,
)
def mark_patient_appointment_no_show(appointment_id: int):
    with Session(engine) as session:
        appointment = mark_appointment_no_show(session, appointment_id)
        session.commit()
        session.refresh(appointment)
        return appointment


@app.get(
    "/appointments/{appointment_id}/status-history",
    response_model=list[AppointmentStatusChangeRead],
)
def read_appointment_status_history(appointment_id: int):
    with Session(engine) as session:
        appointment = session.get(Appointment, appointment_id)
        if appointment is None:
            raise HTTPException(status_code=404, detail="Appointment not found")

        query = (
            select(AppointmentStatusChange)
            .where(AppointmentStatusChange.appointment_id == appointment_id)
            .order_by(
                AppointmentStatusChange.changed_at,
                AppointmentStatusChange.id,
            )
        )
        return list(session.scalars(query).all())

