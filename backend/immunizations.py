"""Immunization history with explicit provenance, scoped reads and retained corrections."""
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.clinical_reference import reference_code
from backend.models import Immunization, Patient
from backend.patient_lifecycle import lock_active_patient


class ImmunizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cvx_code: str = Field(pattern=r"^[0-9]{1,3}$")
    administered_on: date
    source: Literal["clinic", "historical_record", "patient_reported"]
    manufacturer_code: str | None = Field(default=None, pattern=r"^[A-Z0-9]{2,3}$")
    lot_number: str | None = Field(default=None, max_length=100)
    dose_number: int | None = Field(default=None, ge=1, le=30)
    route: str | None = Field(default=None, max_length=80)
    site: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("lot_number", "route", "site", "notes")
    @classmethod
    def clean_text(cls, value):
        return value.strip() or None if value is not None else None


class ImmunizationVoid(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Enter a correction reason.")
        return value


class PortalImmunizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cvx_code: str
    vaccine_name: str
    administered_on: date
    source: str
    manufacturer_name: str | None
    lot_number: str | None
    dose_number: int | None
    route: str | None
    site: str | None


class ImmunizationRead(PortalImmunizationRead):
    patient_id: int
    cvx_release: str
    manufacturer_code: str | None
    mvx_release: str | None
    notes: str | None
    recorded_at: datetime
    voided_at: datetime | None
    void_reason: str | None


def list_immunizations(session: Session, patient_id: int, *, portal: bool = False):
    if session.get(Patient, patient_id) is None:
        raise HTTPException(404, detail="Patient not found")
    query = select(Immunization).where(Immunization.patient_id == patient_id)
    if portal:
        query = query.where(Immunization.voided_at.is_(None))
    return list(session.scalars(query.order_by(
        Immunization.administered_on.desc(), Immunization.id.desc())))


def record_immunization(session: Session, patient_id: int, payload: ImmunizationCreate):
    patient = lock_active_patient(session, patient_id)
    if not patient.date_of_birth <= payload.administered_on <= date.today():
        raise HTTPException(422, detail="Vaccination date must be between the patient's birth and today.")
    release, vaccine = reference_code("cvx", payload.cvx_code)
    if payload.source == "clinic" and vaccine["kind"] != "Active":
        raise HTTPException(422, detail="This code is for historical documentation, not current clinic administration.")
    if session.scalar(select(Immunization.id).where(
        Immunization.patient_id == patient_id, Immunization.cvx_code == vaccine["code"],
        Immunization.administered_on == payload.administered_on,
        Immunization.voided_at.is_(None),
    ).limit(1)) is not None:
        raise HTTPException(409, detail="This vaccination date and code are already recorded.")
    manufacturer = {}
    if payload.manufacturer_code:
        mvx_release, item = reference_code("mvx", payload.manufacturer_code)
        manufacturer = dict(manufacturer_code=item["code"], manufacturer_name=item["name"],
                            mvx_release=mvx_release)
    record = Immunization(patient_id=patient_id, cvx_code=vaccine["code"],
                          vaccine_name=vaccine["name"], cvx_release=release,
                          **payload.model_dump(exclude={"cvx_code", "manufacturer_code"}), **manufacturer)
    session.add(record)
    session.flush()
    return record


def void_immunization(session: Session, record_id: int, payload: ImmunizationVoid):
    record = session.get(Immunization, record_id)
    if record is None:
        raise HTTPException(404, detail="Immunization not found")
    lock_active_patient(session, record.patient_id)
    session.refresh(record)
    if record.voided_at is not None:
        raise HTTPException(409, detail="This immunization has already been corrected.")
    record.voided_at = datetime.now(timezone.utc)
    record.void_reason = payload.reason
    session.flush()
    return record
