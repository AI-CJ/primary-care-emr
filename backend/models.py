from datetime import date

from sqlalchemy import Float, ForeignKey, String, Text
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
    """A draft visit note for a synthetic patient chart."""

    __tablename__ = "encounters"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"), index=True
    )
    visit_date: Mapped[date] = mapped_column()
    reason_for_visit: Mapped[str] = mapped_column(String(200))
    subjective: Mapped[str | None] = mapped_column(Text(), nullable=True)
    objective: Mapped[str | None] = mapped_column(Text(), nullable=True)
    assessment: Mapped[str | None] = mapped_column(Text(), nullable=True)
    plan: Mapped[str | None] = mapped_column(Text(), nullable=True)

