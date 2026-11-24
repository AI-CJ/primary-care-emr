"""Patient-owned communication choices for the synthetic portal."""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.models import PatientCommunicationPreference
from backend.patient_lifecycle import lock_active_patient


class CommunicationPreferencesPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_channel: Literal["portal", "phone", "email"]
    appointment_reminders: bool
    care_updates: bool


def read_communication_preferences(
    session: Session, patient_id: int,
) -> CommunicationPreferencesPayload:
    record = session.get(PatientCommunicationPreference, patient_id)
    if record is None:
        return CommunicationPreferencesPayload(
            preferred_channel="portal", appointment_reminders=False,
            care_updates=False,
        )
    return CommunicationPreferencesPayload(
        preferred_channel=record.preferred_channel,
        appointment_reminders=record.appointment_reminders,
        care_updates=record.care_updates,
    )


def replace_communication_preferences(
    session: Session, patient_id: int, values: CommunicationPreferencesPayload,
) -> CommunicationPreferencesPayload:
    """Replace only the authenticated patient's row; never modify chart history."""
    lock_active_patient(session, patient_id)
    record = session.get(PatientCommunicationPreference, patient_id)
    if record is None:
        record = PatientCommunicationPreference(patient_id=patient_id)
        session.add(record)
    record.preferred_channel = values.preferred_channel
    record.appointment_reminders = values.appointment_reminders
    record.care_updates = values.care_updates
    session.commit()
    return read_communication_preferences(session, patient_id)
