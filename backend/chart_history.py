"""Read-only historical chart context and explicitly shared imaging projections."""
from datetime import date

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import ImagingReport, Patient, PatientBackground


class BackgroundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    patient_id: int
    reviewed_on: date
    medical_history: str
    surgical_history: str
    family_history: str
    social_history: str
    care_context: str


class SharedImagingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    performed_on: date
    reported_on: date
    modality: str
    study: str
    indication: str
    findings: str
    impression: str
    source: str


class ImagingRead(SharedImagingRead):
    patient_id: int
    shared_on: date | None


def _require_chart(session: Session, patient_id: int) -> None:
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")


def read_background(session: Session, patient_id: int) -> PatientBackground | None:
    _require_chart(session, patient_id)
    return session.get(PatientBackground, patient_id)


def list_imaging(session: Session, patient_id: int, *, shared_only: bool = False):
    _require_chart(session, patient_id)
    query = select(ImagingReport).where(ImagingReport.patient_id == patient_id)
    if shared_only:
        query = query.where(ImagingReport.shared_on.is_not(None),
                            ImagingReport.shared_on <= date.today())
    return list(session.scalars(query.order_by(
        ImagingReport.performed_on.desc(), ImagingReport.id.desc())))
