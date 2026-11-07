from datetime import date, datetime, time, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200))
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
    problem_name_at_link: Mapped[str] = mapped_column(String(200), nullable=False)
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
    """A patient-specific staff follow-up item, retained after completion."""

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

