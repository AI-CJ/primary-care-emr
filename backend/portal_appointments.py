"""Appointment summaries for the staff-operated patient portal preview."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Appointment, Patient
from backend.schemas import PortalAppointmentSummary


def list_portal_preview_appointments(
    session: Session, patient_id: int
) -> list[PortalAppointmentSummary]:
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    rows = session.execute(
        select(
            Appointment.id,
            Appointment.scheduled_date,
            Appointment.start_time,
            Appointment.reason_for_visit,
            Appointment.status,
        )
        .where(Appointment.patient_id == patient_id)
        .order_by(
            Appointment.scheduled_date.desc(),
            Appointment.start_time.desc(),
            Appointment.id.desc(),
        )
    )
    return [
        PortalAppointmentSummary(
            id=appointment_id,
            scheduled_date=scheduled_date,
            start_time=start_time,
            reason_for_visit=reason_for_visit,
            status=status,
        )
        for (
            appointment_id, scheduled_date, start_time, reason_for_visit, status
        ) in rows
    ]
