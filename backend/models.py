from datetime import date, datetime, time, timezone

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column()
    preferred_name: Mapped[str | None] = mapped_column(nullable=True)
    middle_name: Mapped[str | None] = mapped_column(nullable=True)
    last_name: Mapped[str] = mapped_column()
    suffix: Mapped[str | None] = mapped_column(nullable=True)
    date_of_birth: Mapped[date] = mapped_column()
    pronouns: Mapped[str | None] = mapped_column(nullable=True)
    custom_pronouns: Mapped[str | None] = mapped_column(nullable=True)
    sex_at_birth: Mapped[str] = mapped_column(nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PatientLifecycleEvent(Base):
    """Append-only status transitions. Archiving never deletes chart data."""

    __tablename__ = "patient_lifecycle_events"
    __table_args__ = (
        CheckConstraint("action IN ('archive', 'reactivate')", name="ck_patient_lifecycle_action"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False,
    )
    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey("user_accounts.id", ondelete="RESTRICT"), index=True, nullable=False,
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(512))
    icd10_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    icd10_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    icd10_release: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    onset_date: Mapped[date | None] = mapped_column(nullable=True)
    resolved_date: Mapped[date | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200))
    strength: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    route: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[date | None] = mapped_column(nullable=True)
    end_date: Mapped[date | None] = mapped_column(nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text(), nullable=True)
    indications: Mapped[list["MedicationIndication"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="MedicationIndication.problem_id"
    )


class MedicationIndication(Base):
    """Clinician-selected diagnosis with the name/code recorded at selection."""

    __tablename__ = "medication_indications"
    __table_args__ = (UniqueConstraint("medication_id", "problem_id", name="uq_medication_indication"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    medication_id: Mapped[int] = mapped_column(ForeignKey("medications.id", ondelete="RESTRICT"), index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="RESTRICT"), index=True)
    problem_name: Mapped[str] = mapped_column(String(512))
    icd10_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    icd10_release: Mapped[str | None] = mapped_column(String(16), nullable=True)


class Allergy(Base):
    __tablename__ = "allergies"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        index=True,
    )
    allergen: Mapped[str] = mapped_column(String(200))
    reaction: Mapped[str | None] = mapped_column(String(300), nullable=True)
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    onset_date: Mapped[date | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)


class Vital(Base):
    __tablename__ = "vitals"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"), index=True
    )
    recorded_on: Mapped[date] = mapped_column()
    systolic_bp: Mapped[int | None] = mapped_column(nullable=True)
    diastolic_bp: Mapped[int | None] = mapped_column(nullable=True)
    heart_rate: Mapped[int | None] = mapped_column(nullable=True)
    respiratory_rate: Mapped[int | None] = mapped_column(nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float(), nullable=True)
    oxygen_saturation: Mapped[int | None] = mapped_column(nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float(), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float(), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)


class Encounter(Base):
    """A visit note for a synthetic patient chart."""

    __tablename__ = "encounters"
    __table_args__ = (
        UniqueConstraint("appointment_id", name="uq_encounters_appointment_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"), index=True
    )
    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointments.id"), nullable=True
    )
    visit_date: Mapped[date] = mapped_column()
    reason_for_visit: Mapped[str] = mapped_column(String(200))
    subjective: Mapped[str | None] = mapped_column(Text(), nullable=True)
    objective: Mapped[str | None] = mapped_column(Text(), nullable=True)
    assessment: Mapped[str | None] = mapped_column(Text(), nullable=True)
    plan: Mapped[str | None] = mapped_column(Text(), nullable=True)
    patient_instructions: Mapped[str | None] = mapped_column(Text(), nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class EncounterAddendum(Base):
    """A permanent addition to a finalized visit note."""

    __tablename__ = "encounter_addenda"

    id: Mapped[int] = mapped_column(primary_key=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey("encounters.id", ondelete="RESTRICT"), index=True
    )
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class EncounterProblem(Base):
    """A visit's reference to a chart problem, frozen at time of linking."""

    __tablename__ = "encounter_problems"
    __table_args__ = (
        UniqueConstraint(
            "encounter_id", "problem_id", name="uq_encounter_problems_visit_problem"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False
    )
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    problem_name_at_link: Mapped[str] = mapped_column(String(512), nullable=False)
    icd10_code_at_link: Mapped[str | None] = mapped_column(String(8), nullable=True)
    icd10_release_at_link: Mapped[str | None] = mapped_column(String(16), nullable=True)
    problem_status_at_link: Mapped[str] = mapped_column(String(20), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class EncounterVital(Base):
    """A historical snapshot of a vital record linked to a visit."""

    __tablename__ = "encounter_vitals"
    __table_args__ = (
        UniqueConstraint("encounter_id", "vital_id", name="uq_encounter_vitals_visit_vital"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False
    )
    vital_id: Mapped[int] = mapped_column(
        ForeignKey("vitals.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    recorded_on_at_link: Mapped[date] = mapped_column(nullable=False)
    systolic_bp_at_link: Mapped[int | None] = mapped_column(nullable=True)
    diastolic_bp_at_link: Mapped[int | None] = mapped_column(nullable=True)
    heart_rate_at_link: Mapped[int | None] = mapped_column(nullable=True)
    respiratory_rate_at_link: Mapped[int | None] = mapped_column(nullable=True)
    temperature_c_at_link: Mapped[float | None] = mapped_column(Float(), nullable=True)
    oxygen_saturation_at_link: Mapped[int | None] = mapped_column(nullable=True)
    height_cm_at_link: Mapped[float | None] = mapped_column(Float(), nullable=True)
    weight_kg_at_link: Mapped[float | None] = mapped_column(Float(), nullable=True)
    notes_at_link: Mapped[str | None] = mapped_column(Text(), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

class EncounterMedication(Base):
    """A historical snapshot of a chart medication linked to a visit."""

    __tablename__ = "encounter_medications"
    __table_args__ = (
        UniqueConstraint(
            "encounter_id", "medication_id", name="uq_encounter_medications_visit_medication"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False
    )
    medication_id: Mapped[int] = mapped_column(
        ForeignKey("medications.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    name_at_link: Mapped[str] = mapped_column(String(200), nullable=False)
    strength_at_link: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dose_at_link: Mapped[str | None] = mapped_column(String(100), nullable=True)
    route_at_link: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency_at_link: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status_at_link: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date_at_link: Mapped[date | None] = mapped_column(nullable=True)
    end_date_at_link: Mapped[date | None] = mapped_column(nullable=True)
    instructions_at_link: Mapped[str | None] = mapped_column(Text(), nullable=True)
    indications_at_link: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False, server_default=text("'[]'"))
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class EncounterAllergy(Base):
    """A historical snapshot of a chart allergy linked to a visit."""

    __tablename__ = "encounter_allergies"
    __table_args__ = (
        UniqueConstraint("encounter_id", "allergy_id", name="uq_encounter_allergies_visit_allergy"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False
    )
    allergy_id: Mapped[int] = mapped_column(
        ForeignKey("allergies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    allergen_at_link: Mapped[str] = mapped_column(String(200), nullable=False)
    reaction_at_link: Mapped[str | None] = mapped_column(String(300), nullable=True)
    severity_at_link: Mapped[str] = mapped_column(String(20), nullable=False)
    status_at_link: Mapped[str] = mapped_column(String(20), nullable=False)
    onset_date_at_link: Mapped[date | None] = mapped_column(nullable=True)
    notes_at_link: Mapped[str | None] = mapped_column(Text(), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class LabOrder(Base):
    """A synthetic lab test request made during a visit."""

    __tablename__ = "lab_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey("encounters.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    clinical_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ordered", nullable=False)
    ordered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    indications: Mapped[list["LabOrderIndication"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="LabOrderIndication.problem_id"
    )


class LabOrderIndication(Base):
    """The recorded diagnosis for a test request, retained with its history."""

    __tablename__ = "lab_order_indications"
    __table_args__ = (UniqueConstraint("lab_order_id", "problem_id", name="uq_lab_order_indication"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    lab_order_id: Mapped[int] = mapped_column(ForeignKey("lab_orders.id", ondelete="RESTRICT"), index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="RESTRICT"), index=True)
    problem_name: Mapped[str] = mapped_column(String(512))
    icd10_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    icd10_release: Mapped[str | None] = mapped_column(String(16), nullable=True)


class LabResult(Base):
    """A permanent synthetic result attached to a lab request."""

    __tablename__ = "lab_results"
    __table_args__ = (
        UniqueConstraint("lab_order_id", name="uq_lab_results_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lab_order_id: Mapped[int] = mapped_column(
        ForeignKey("lab_orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    collected_on: Mapped[date] = mapped_column(nullable=False)
    result_text: Mapped[str] = mapped_column(Text(), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Referral(Base):
    """A synthetic specialist referral request from a visit."""

    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(primary_key=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey("encounters.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    specialty: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text(), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="requested", nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    seen_on: Mapped[date | None] = mapped_column(nullable=True)
    follow_up_summary: Mapped[str | None] = mapped_column(Text(), nullable=True)


class CareGoal(Base):
    """A longitudinal care goal that stays in the chart after completion."""

    __tablename__ = "care_goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_date: Mapped[date | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completion_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    discontinued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    discontinuation_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)


class CareGoalProgress(Base):
    """A dated, append-only progress entry for a care goal."""

    __tablename__ = "care_goal_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(
        ForeignKey("care_goals.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    note: Mapped[str] = mapped_column(Text(), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class FollowUpTask(Base):
    """A patient-specific staff follow-up item, retained after closure."""

    __tablename__ = "follow_up_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    care_goal_id: Mapped[int | None] = mapped_column(
        ForeignKey("care_goals.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    details: Mapped[str | None] = mapped_column(Text(), nullable=True)
    due_date: Mapped[date | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completion_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)


class FollowUpDueDateChange(Base):
    """An append-only record of a staff follow-up deadline change."""

    __tablename__ = "follow_up_due_date_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("follow_up_tasks.id", ondelete="RESTRICT"),
        index=True, nullable=False,
    )
    previous_due_date: Mapped[date | None] = mapped_column(nullable=True)
    new_due_date: Mapped[date | None] = mapped_column(nullable=True)
    reason: Mapped[str] = mapped_column(Text(), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False,
    )


class Appointment(Base):
    """A clinic-local appointment for a synthetic patient."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"), index=True
    )
    scheduled_date: Mapped[date] = mapped_column()
    start_time: Mapped[time] = mapped_column()
    duration_minutes: Mapped[int] = mapped_column()
    reason_for_visit: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))


class AppointmentStatusChange(Base):
    """A recorded status change, not a user-attributed audit event."""

    __tablename__ = "appointment_status_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id"), index=True
    )
    previous_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    new_status: Mapped[str] = mapped_column(String(20))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )



class UserAccount(Base):
    """An identity for a staff member or one synthetic patient."""

    __tablename__ = "user_accounts"
    __table_args__ = (
        CheckConstraint(
            "(account_type = 'staff' AND staff_role IS NOT NULL "
            "AND staff_role IN ('admin', 'clinician', 'front_desk') "
            "AND patient_id IS NULL) OR (account_type = 'patient' "
            "AND staff_role IS NULL AND patient_id IS NOT NULL)",
            name="ck_user_accounts_role_scope",
        ),
        CheckConstraint("username = lower(username)", name="ck_user_accounts_username_lower"),
        UniqueConstraint("patient_id", name="uq_user_accounts_patient_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    staff_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    patient_id: Mapped[int | None] = mapped_column(
        ForeignKey("patients.id", ondelete="RESTRICT"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PatientCommunicationPreference(Base):
    """One mutable communication preference record per synthetic patient."""

    __tablename__ = "patient_communication_preferences"
    __table_args__ = (
        CheckConstraint(
            "preferred_channel IN ('portal', 'phone', 'email')",
            name="ck_patient_communication_preferred_channel",
        ),
    )

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="RESTRICT"), primary_key=True,
    )
    preferred_channel: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="portal",
    )
    appointment_reminders: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="false",
    )
    care_updates: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="false",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        nullable=False,
    )



class AppointmentChangeRequest(Base):
    """A patient request awaiting human review; clinical history is unaffected."""

    __tablename__ = "appointment_change_requests"
    __table_args__ = (
        CheckConstraint("kind IN ('cancel', 'reschedule')",
                        name="ck_appointment_change_kind"),
        CheckConstraint("status IN ('pending', 'reviewed')",
                        name="ck_appointment_change_status"),
        Index("uq_appointment_change_requests_pending", "appointment_id",
              unique=True, postgresql_where=text("status = 'pending'"),
              sqlite_where=text("status = 'pending'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="RESTRICT"), index=True, nullable=False,
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )


class AuditEvent(Base):
    """Persistent, append-only authentication and clinical access metadata."""

    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('login_success', 'login_failure', 'logout', "
            "'clinical_read', 'clinical_write', 'access_denied')",
            name="ck_audit_events_event_type",
        ),
        CheckConstraint(
            "status_code BETWEEN 100 AND 599", name="ck_audit_events_status_code"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_accounts.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    # Attempted chart IDs may not exist; do not enforce a foreign key here.
    subject_patient_id: Mapped[int | None] = mapped_column(index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)
    route_template: Mapped[str] = mapped_column(String(160), nullable=False)
    http_method: Mapped[str] = mapped_column(String(8), nullable=False)
    status_code: Mapped[int] = mapped_column(nullable=False)
    resource_id: Mapped[int | None] = mapped_column(nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class UserSession(Base):
    """A revocable session; only the bearer token's digest is stored."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_accounts.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class PatientBackground(Base):
    """Recorded longitudinal context, separate from demographic identity."""

    __tablename__ = "patient_backgrounds"
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="RESTRICT"), primary_key=True)
    reviewed_on: Mapped[date] = mapped_column(nullable=False)
    medical_history: Mapped[str] = mapped_column(Text(), nullable=False)
    surgical_history: Mapped[str] = mapped_column(Text(), nullable=False)
    family_history: Mapped[str] = mapped_column(Text(), nullable=False)
    social_history: Mapped[str] = mapped_column(Text(), nullable=False)
    care_context: Mapped[str] = mapped_column(Text(), nullable=False)


class ImagingReport(Base):
    """Historical report text, not an imaging order or a stored DICOM study."""

    __tablename__ = "imaging_reports"
    __table_args__ = (
        CheckConstraint("shared_on IS NULL OR shared_on >= reported_on", name="ck_imaging_report_share_date"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False)
    performed_on: Mapped[date] = mapped_column(nullable=False)
    reported_on: Mapped[date] = mapped_column(nullable=False)
    modality: Mapped[str] = mapped_column(String(40), nullable=False)
    study: Mapped[str] = mapped_column(String(200), nullable=False)
    indication: Mapped[str] = mapped_column(Text(), nullable=False)
    findings: Mapped[str] = mapped_column(Text(), nullable=False)
    impression: Mapped[str] = mapped_column(Text(), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    shared_on: Mapped[date | None] = mapped_column(nullable=True)
