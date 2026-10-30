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

    @field_validator("subjective", "objective", "assessment", "plan")
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
    pass


class EncounterRead(EncounterBase):
    id: int
    patient_id: int

    model_config = ConfigDict(from_attributes=True)


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

