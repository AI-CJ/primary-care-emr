from datetime import date, datetime, time
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


SexAtBirth = Literal[
    "female",
    "male",
    "intersex",
    "unknown",
    "prefer_not_to_answer",
]

Pronouns = Literal[
    "he/him",
    "she/her",
    "they/them",
    "other",
    "prefer_not_to_answer",
]

ProblemStatus = Literal[
    "active",
    "resolved",
]

MedicationStatus = Literal[
    "active",
    "completed",
    "discontinued",
]

AllergySeverity = Literal[
    "mild",
    "moderate",
    "severe",
    "unknown",
]

AllergyStatus = Literal[
    "active",
    "inactive",
]

AppointmentStatus = Literal[
    "scheduled",
    "checked_in",
    "completed",
    "cancelled",
    "no_show",
]


class PatientBase(BaseModel):
    first_name: str = Field(max_length=100)
    preferred_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(max_length=100)
    suffix: str | None = Field(default=None, max_length=20)

    date_of_birth: date
    sex_at_birth: SexAtBirth

    pronouns: Pronouns | None = None
    custom_pronouns: str | None = Field(default=None, max_length=100)

    @field_validator("first_name", "last_name")
    @classmethod
    def required_names_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Name cannot be blank")

        return value

    @field_validator(
        "preferred_name",
        "middle_name",
        "suffix",
        "custom_pronouns",
    )
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None

    @field_validator("date_of_birth")
    @classmethod
    def date_of_birth_cannot_be_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Date of birth cannot be in the future")

        return value

    @model_validator(mode="after")
    def validate_custom_pronouns(self):
        if self.pronouns == "other" and not self.custom_pronouns:
            raise ValueError(
                "Custom pronouns are required when pronouns is 'other'"
            )

        if self.pronouns != "other":
            self.custom_pronouns = None

        return self


class PatientCreate(PatientBase):
    pass


class PatientRead(PatientBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProblemBase(BaseModel):
    name: str = Field(max_length=200)
    status: ProblemStatus = "active"
    onset_date: date | None = None
    resolved_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def problem_name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Problem name cannot be blank")

        return value

    @field_validator("notes")
    @classmethod
    def clean_problem_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None

    @field_validator("onset_date", "resolved_date")
    @classmethod
    def problem_dates_cannot_be_future(
        cls,
        value: date | None,
    ) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Problem dates cannot be in the future")

        return value

    @model_validator(mode="after")
    def validate_problem_dates(self):
        if self.status == "active":
            self.resolved_date = None

        if (
            self.onset_date
            and self.resolved_date
            and self.resolved_date < self.onset_date
        ):
            raise ValueError("Resolved date cannot be before onset date")

        return self


class ProblemCreate(ProblemBase):
    pass


class ProblemRead(ProblemBase):
    id: int
    patient_id: int

    model_config = ConfigDict(from_attributes=True)


class PortalProblemSummary(BaseModel):
    id: int
    name: str
    status: ProblemStatus
    onset_date: date | None
    resolved_date: date | None

    model_config = ConfigDict(extra="forbid")


class MedicationBase(BaseModel):
    name: str = Field(max_length=200)
    strength: str | None = Field(default=None, max_length=100)
    dose: str | None = Field(default=None, max_length=100)
    route: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    status: MedicationStatus = "active"
    start_date: date | None = None
    end_date: date | None = None
    instructions: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def medication_name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Medication name cannot be blank")

        return value

    @field_validator(
        "strength",
        "dose",
        "route",
        "frequency",
        "instructions",
    )
    @classmethod
    def clean_medication_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_medication_dates(self):
        if self.status == "active":
            self.end_date = None

        if (
            self.start_date
            and self.end_date
            and self.end_date < self.start_date
        ):
            raise ValueError("End date cannot be before start date")

        return self


class MedicationCreate(MedicationBase):
    pass


class MedicationRead(MedicationBase):
    id: int
    patient_id: int

    model_config = ConfigDict(from_attributes=True)


class PortalMedicationSummary(BaseModel):
    id: int
    name: str
    strength: str | None
    dose: str | None
    frequency: str | None
    status: MedicationStatus
    start_date: date | None
    end_date: date | None
    instructions: str | None

    model_config = ConfigDict(extra="forbid")


class AllergyBase(BaseModel):
    allergen: str = Field(max_length=200)
    reaction: str | None = Field(default=None, max_length=300)
    severity: AllergySeverity = "unknown"
    status: AllergyStatus = "active"
    onset_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("allergen")
    @classmethod
    def allergen_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Allergen cannot be blank")

        return value

    @field_validator("reaction", "notes")
    @classmethod
    def clean_allergy_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None

    @field_validator("onset_date")
    @classmethod
    def allergy_onset_cannot_be_future(
        cls,
        value: date | None,
    ) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Allergy onset date cannot be in the future")

        return value


class AllergyCreate(AllergyBase):
    pass


class AllergyRead(AllergyBase):
    id: int
    patient_id: int

    model_config = ConfigDict(from_attributes=True)


class PortalAllergySummary(BaseModel):
    id: int
    allergen: str
    reaction: str | None
    severity: AllergySeverity
    status: AllergyStatus
    onset_date: date | None

    model_config = ConfigDict(extra="forbid")


class VitalBase(BaseModel):
    recorded_on: date
    systolic_bp: int | None = Field(default=None, ge=1, le=400)
    diastolic_bp: int | None = Field(default=None, ge=1, le=300)
    heart_rate: int | None = Field(default=None, ge=1, le=350)
    respiratory_rate: int | None = Field(default=None, ge=1, le=150)
    temperature_c: float | None = Field(
        default=None, ge=0, le=60, allow_inf_nan=False
    )
    oxygen_saturation: int | None = Field(default=None, ge=0, le=100)
    height_cm: float | None = Field(
        default=None, gt=0, le=300, allow_inf_nan=False
    )
    weight_kg: float | None = Field(
        default=None, gt=0, le=1000, allow_inf_nan=False
    )
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("recorded_on")
    @classmethod
    def recorded_on_cannot_be_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Recorded date cannot be in the future")
        return value

    @field_validator("notes")
    @classmethod
    def clean_vital_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_measurements(self):
        if (self.systolic_bp is None) != (self.diastolic_bp is None):
            raise ValueError(
                "Both systolic and diastolic blood pressure are required together"
            )
        if (
            self.systolic_bp is not None
            and self.diastolic_bp is not None
            and self.systolic_bp < self.diastolic_bp
        ):
            raise ValueError(
                "Systolic blood pressure cannot be below diastolic blood pressure"
            )
        measurements = (
            self.systolic_bp, self.diastolic_bp, self.heart_rate,
            self.respiratory_rate, self.temperature_c,
            self.oxygen_saturation, self.height_cm, self.weight_kg,
        )
        if all(value is None for value in measurements):
            raise ValueError("At least one vital measurement is required")
        return self


class VitalCreate(VitalBase):
    pass


class VitalRead(VitalBase):
    id: int
    patient_id: int

    model_config = ConfigDict(from_attributes=True)


class EncounterBase(BaseModel):
    visit_date: date
    reason_for_visit: str = Field(max_length=200)
    subjective: str | None = Field(default=None, max_length=4000)
    objective: str | None = Field(default=None, max_length=4000)
    assessment: str | None = Field(default=None, max_length=4000)
    plan: str | None = Field(default=None, max_length=4000)
    patient_instructions: str | None = Field(default=None, max_length=4000)

    @field_validator("visit_date")
    @classmethod
    def visit_date_cannot_be_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Visit date cannot be in the future")
        return value

    @field_validator("reason_for_visit")
    @classmethod
    def reason_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Reason for visit cannot be blank")
        return value

    @field_validator("subjective", "objective", "assessment", "plan", "patient_instructions")
    @classmethod
    def clean_note_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def at_least_one_note_section(self):
        if not any(
            (self.subjective, self.objective, self.assessment, self.plan)
        ):
            raise ValueError("Complete at least one visit note section")
        return self


class EncounterCreate(EncounterBase):
    appointment_id: int | None = Field(default=None, gt=0)


class EncounterUpdate(EncounterBase):
    # The link between a visit note and its appointment is permanent.
    model_config = ConfigDict(extra="forbid")


class EncounterRead(EncounterBase):
    id: int
    patient_id: int
    appointment_id: int | None
    finalized_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PortalVisitSummary(BaseModel):
    id: int
    visit_date: date
    reason_for_visit: str
    patient_instructions: str | None

    model_config = ConfigDict(extra="forbid")


class EncounterAddendumCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def content_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Addendum cannot be blank")
        return value


class EncounterAddendumRead(EncounterAddendumCreate):
    id: int
    encounter_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class EncounterProblemLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: int = Field(gt=0)


class EncounterProblemRead(EncounterProblemLinkCreate):
    id: int
    encounter_id: int
    problem_name_at_link: str
    problem_status_at_link: ProblemStatus
    linked_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")



class EncounterVitalLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vital_id: int = Field(gt=0)


class EncounterVitalRead(EncounterVitalLinkCreate):
    id: int
    encounter_id: int
    recorded_on_at_link: date
    systolic_bp_at_link: int | None
    diastolic_bp_at_link: int | None
    heart_rate_at_link: int | None
    respiratory_rate_at_link: int | None
    temperature_c_at_link: float | None
    oxygen_saturation_at_link: int | None
    height_cm_at_link: float | None
    weight_kg_at_link: float | None
    notes_at_link: str | None
    linked_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class EncounterMedicationLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medication_id: int = Field(gt=0)


class EncounterMedicationRead(EncounterMedicationLinkCreate):
    id: int
    encounter_id: int
    name_at_link: str
    strength_at_link: str | None
    dose_at_link: str | None
    route_at_link: str | None
    frequency_at_link: str | None
    status_at_link: MedicationStatus
    start_date_at_link: date | None
    end_date_at_link: date | None
    instructions_at_link: str | None
    linked_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class EncounterAllergyLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allergy_id: int = Field(gt=0)


class EncounterAllergyRead(EncounterAllergyLinkCreate):
    id: int
    encounter_id: int
    allergen_at_link: str
    reaction_at_link: str | None
    severity_at_link: AllergySeverity
    status_at_link: AllergyStatus
    onset_date_at_link: date | None
    notes_at_link: str | None
    linked_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class LabOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_name: str = Field(min_length=1, max_length=200)
    priority: Literal["routine", "urgent"] = "routine"
    clinical_reason: str | None = Field(default=None, max_length=1000)

    @field_validator("test_name")
    @classmethod
    def test_name_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Lab test name cannot be blank")
        return value

    @field_validator("clinical_reason")
    @classmethod
    def clean_clinical_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class LabOrderCancel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def reason_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Cancellation reason cannot be blank")
        return value


class LabOrderRead(LabOrderCreate):
    id: int
    encounter_id: int
    status: Literal["ordered", "resulted", "cancelled"]
    ordered_at: datetime
    cancelled_at: datetime | None
    cancellation_reason: str | None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class LabResultCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collected_on: date
    result_text: str = Field(min_length=1, max_length=4000)

    @field_validator("collected_on")
    @classmethod
    def collected_on_cannot_be_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Collection date cannot be in the future")
        return value

    @field_validator("result_text")
    @classmethod
    def result_text_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Lab result cannot be blank")
        return value


class LabResultRead(LabResultCreate):
    id: int
    lab_order_id: int
    reported_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class PatientLabOrderRead(LabOrderRead):
    visit_date: date
    result: LabResultRead | None



class PortalLabResultSummary(BaseModel):
    collected_on: date
    result_text: str
    reported_at: datetime

    model_config = ConfigDict(extra="forbid")


class PortalLabOrderSummary(BaseModel):
    id: int
    test_name: str
    status: Literal["ordered", "resulted", "cancelled"]
    ordered_at: datetime
    cancelled_at: datetime | None
    result: PortalLabResultSummary | None

    model_config = ConfigDict(extra="forbid")


class PendingLabOrderRead(LabOrderRead):
    patient_id: int
    patient_name: str
    visit_date: date


class ReferralCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    specialty: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1000)
    priority: Literal["routine", "urgent"] = "routine"

    @field_validator("specialty", "reason")
    @classmethod
    def required_text_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class ReferralCancel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def reason_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Cancellation reason cannot be blank")
        return value


class ReferralComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seen_on: date
    follow_up_summary: str = Field(min_length=1, max_length=4000)

    @field_validator("seen_on")
    @classmethod
    def visit_date_cannot_be_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Specialist visit date cannot be in the future")
        return value

    @field_validator("follow_up_summary")
    @classmethod
    def follow_up_summary_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Follow-up summary cannot be blank")
        return value


class ReferralRead(ReferralCreate):
    id: int
    encounter_id: int
    status: Literal["requested", "cancelled", "completed"]
    requested_at: datetime
    cancelled_at: datetime | None
    cancellation_reason: str | None
    completed_at: datetime | None
    seen_on: date | None
    follow_up_summary: str | None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class PatientReferralRead(ReferralRead):
    visit_date: date


class PortalReferralSummary(BaseModel):
    id: int
    specialty: str
    priority: Literal["routine", "urgent"]
    status: Literal["requested", "cancelled", "completed"]
    visit_date: date
    seen_on: date | None

    model_config = ConfigDict(extra="forbid")


class PendingReferralRead(ReferralRead):
    patient_id: int
    patient_name: str
    visit_date: date


class CareGoalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    target_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Care goal cannot be blank")
        return value


class CareGoalComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completion_note: str = Field(min_length=1, max_length=2000)

    @field_validator("completion_note")
    @classmethod
    def completion_note_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Completion note cannot be blank")
        return value


class CareGoalDiscontinue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def reason_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Discontinuation reason cannot be blank")
        return value


class CareGoalRead(CareGoalCreate):
    id: int
    patient_id: int
    status: Literal["active", "completed", "discontinued"]
    created_at: datetime
    completed_at: datetime | None
    completion_note: str | None
    discontinued_at: datetime | None
    discontinuation_reason: str | None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ActiveCareGoalRead(CareGoalRead):
    patient_name: str
    is_overdue: bool


class CareGoalProgressCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=1, max_length=2000)

    @field_validator("note")
    @classmethod
    def note_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Progress note cannot be blank")
        return value


class CareGoalProgressRead(CareGoalProgressCreate):
    id: int
    goal_id: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class FollowUpTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    details: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None
    care_goal_id: int | None = Field(default=None, gt=0)

    @field_validator("title")
    @classmethod
    def title_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task title cannot be blank")
        return value

    @field_validator("details")
    @classmethod
    def normalize_details(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class FollowUpTaskComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completion_note: str = Field(min_length=1, max_length=2000)

    @field_validator("completion_note")
    @classmethod
    def completion_note_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Completion note cannot be blank")
        return value


class FollowUpTaskCancel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def reason_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Cancellation reason cannot be blank")
        return value


class FollowUpTaskReschedule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Required, including when explicitly clearing a deadline.
    due_date: date | None
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def reason_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Rescheduling reason cannot be blank")
        return value


class FollowUpDueDateChangeRead(BaseModel):
    id: int
    task_id: int
    previous_due_date: date | None
    new_due_date: date | None
    reason: str
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class FollowUpTaskRead(FollowUpTaskCreate):
    id: int
    patient_id: int
    status: Literal["open", "completed", "cancelled"]
    created_at: datetime
    completed_at: datetime | None
    completion_note: str | None
    cancelled_at: datetime | None
    cancellation_reason: str | None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class OpenFollowUpTaskRead(FollowUpTaskRead):
    patient_name: str
    is_overdue: bool


class AppointmentBase(BaseModel):
    scheduled_date: date
    start_time: time
    duration_minutes: int = Field(default=30, ge=15, le=180, multiple_of=15)
    reason_for_visit: str = Field(max_length=200)
    status: AppointmentStatus = "scheduled"

    @field_validator("reason_for_visit")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Reason for visit cannot be blank")
        return value

    @field_validator("start_time")
    @classmethod
    def start_time_must_be_clinic_local(cls, value: time) -> time:
        if value.tzinfo is not None:
            raise ValueError("Start time must be clinic-local without a timezone offset")
        return value


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentRead(AppointmentBase):
    id: int
    patient_id: int

    model_config = ConfigDict(from_attributes=True)


class AppointmentStatusChangeRead(BaseModel):
    id: int
    appointment_id: int
    previous_status: AppointmentStatus | None
    new_status: AppointmentStatus
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SchedulePatientRead(BaseModel):
    id: int
    first_name: str
    preferred_name: str | None
    last_name: str
    date_of_birth: date

    model_config = ConfigDict(from_attributes=True)


class ScheduleEntryRead(BaseModel):
    appointment: AppointmentRead
    patient: SchedulePatientRead



class PatientTimelineEntry(BaseModel):
    """A dated chart item with its current status, not an audit event."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "visit", "vitals", "lab_order", "lab_result",
        "referral", "care_goal", "follow_up",
    ]
    record_id: int = Field(gt=0)
    occurred_on: date
    title: str
    status: str
