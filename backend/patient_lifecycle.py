"""Admin-only archive/reactivation of synthetic charts without deleting history."""

from datetime import datetime, timezone

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import (
    Appointment, Patient, PatientLifecycleEvent, UserAccount, UserSession,
)


class PatientLifecycleEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    actor_user_id: int
    action: str
    changed_at: datetime


def _lock_patient(session: Session, patient_id: int) -> Patient:
    patient = session.scalar(
        select(Patient).where(Patient.id == patient_id).with_for_update()
    )
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def archive_patient(session: Session, patient_id: int, actor_id: int) -> Patient:
    """Reject unresolved visits and revoke sessions in the status transaction."""
    patient = _lock_patient(session, patient_id)
    if patient.archived_at is not None:
        raise HTTPException(status_code=409, detail="Chart is already archived")

    unresolved = session.scalar(
        select(Appointment.id).where(
            Appointment.patient_id == patient_id,
            Appointment.status.in_(("scheduled", "checked_in")),
        ).limit(1)
    )
    if unresolved is not None:
        raise HTTPException(
            status_code=409,
            detail="Resolve scheduled and checked-in appointments before archiving",
        )

    now = datetime.now(timezone.utc)
    patient.archived_at = now
    account = session.scalar(
        select(UserAccount).where(
            UserAccount.account_type == "patient",
            UserAccount.patient_id == patient_id,
        )
    )
    if account is not None:
        for active_session in session.scalars(
            select(UserSession).where(
                UserSession.user_id == account.id,
                UserSession.revoked_at.is_(None),
            )
        ):
            active_session.revoked_at = now
    session.add(PatientLifecycleEvent(
        patient_id=patient_id, actor_user_id=actor_id, action="archive",
    ))
    session.commit()
    session.refresh(patient)
    return patient


def reactivate_patient(session: Session, patient_id: int, actor_id: int) -> Patient:
    patient = _lock_patient(session, patient_id)
    if patient.archived_at is None:
        raise HTTPException(status_code=409, detail="Chart is already active")

    patient.archived_at = None
    session.add(PatientLifecycleEvent(
        patient_id=patient_id, actor_user_id=actor_id, action="reactivate",
    ))
    session.commit()
    session.refresh(patient)
    return patient


def list_patient_lifecycle_events(
    session: Session, patient_id: int,
) -> list[PatientLifecycleEvent]:
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return list(session.scalars(
        select(PatientLifecycleEvent)
        .where(PatientLifecycleEvent.patient_id == patient_id)
        .order_by(PatientLifecycleEvent.id.desc())
        .limit(100)
    ))
