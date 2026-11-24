"""Patient appointment change requests are an administrative queue, not schedule edits."""

from datetime import date, datetime, timezone
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Appointment, AppointmentChangeRequest, Patient
from backend.patient_lifecycle import lock_active_patient


class AppointmentChangeRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    appointment_id: int = Field(gt=0)
    kind: Literal["cancel", "reschedule"]


class AppointmentChangeRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    appointment_id: int
    kind: Literal["cancel", "reschedule"]
    status: Literal["pending", "reviewed"]
    created_at: datetime
    reviewed_at: datetime | None


class StaffAppointmentChangeRequestRead(AppointmentChangeRequestRead):
    patient_id: int


def submit_appointment_change_request(
    session: Session, patient_id: int, payload: AppointmentChangeRequestCreate,
) -> AppointmentChangeRequest:
    # Match archival lock ordering before the appointment-level scheduling lock.
    lock_active_patient(session, patient_id)
    appointment = session.scalar(
        select(Appointment).where(Appointment.id == payload.appointment_id).with_for_update()
    )
    if appointment is None or appointment.patient_id != patient_id:
        # Avoid revealing whether another patient's appointment exists.
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status != "scheduled" or appointment.scheduled_date < date.today():
        raise HTTPException(
            status_code=409, detail="Only current or future scheduled visits can be changed.",
        )
    pending = session.scalar(
        select(AppointmentChangeRequest.id).where(
            AppointmentChangeRequest.appointment_id == appointment.id,
            AppointmentChangeRequest.status == "pending",
        )
    )
    if pending is not None:
        raise HTTPException(status_code=409, detail="A change request is already pending.")

    record = AppointmentChangeRequest(
        appointment_id=appointment.id, patient_id=patient_id,
        kind=payload.kind, status="pending",
    )
    session.add(record)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="A change request is already pending.",
        ) from exc
    session.refresh(record)
    return record


def list_patient_change_requests(
    session: Session, patient_id: int,
) -> list[AppointmentChangeRequest]:
    return list(session.scalars(
        select(AppointmentChangeRequest)
        .where(AppointmentChangeRequest.patient_id == patient_id)
        .order_by(AppointmentChangeRequest.created_at.desc(), AppointmentChangeRequest.id.desc())
        .limit(100)
    ))


def list_pending_change_requests(session: Session) -> list[AppointmentChangeRequest]:
    return list(session.scalars(
        select(AppointmentChangeRequest)
        .join(Patient, Patient.id == AppointmentChangeRequest.patient_id)
        .where(
            AppointmentChangeRequest.status == "pending",
            Patient.archived_at.is_(None),
        )
        .order_by(AppointmentChangeRequest.created_at, AppointmentChangeRequest.id)
        .limit(100)
    ))


def review_change_request(session: Session, request_id: int) -> AppointmentChangeRequest:
    patient_id = session.scalar(
        select(AppointmentChangeRequest.patient_id).where(
            AppointmentChangeRequest.id == request_id,
        )
    )
    if patient_id is None:
        raise HTTPException(status_code=404, detail="Request not found")

    # Lock the chart before the queue row so review cannot race archival.
    lock_active_patient(session, patient_id)
    record = session.scalar(
        select(AppointmentChangeRequest)
        .where(AppointmentChangeRequest.id == request_id)
        .with_for_update()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if record.status != "pending":
        raise HTTPException(status_code=409, detail="Request has already been reviewed")
    record.status = "reviewed"
    record.reviewed_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(record)
    return record
