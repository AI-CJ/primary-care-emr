"""Preserve the vital signs referenced by a draft visit note."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Encounter, EncounterVital, Vital
from backend.schemas import EncounterVitalLinkCreate


SNAPSHOT_FIELDS = (
    "recorded_on", "systolic_bp", "diastolic_bp", "heart_rate",
    "respiratory_rate", "temperature_c", "oxygen_saturation",
    "height_cm", "weight_kg", "notes",
)


def list_encounter_vitals(session: Session, encounter_id: int) -> list[EncounterVital]:
    if session.get(Encounter, encounter_id) is None:
        raise HTTPException(status_code=404, detail="Visit note not found")

    query = (
        select(EncounterVital)
        .where(EncounterVital.encounter_id == encounter_id)
        .order_by(EncounterVital.id)
    )
    return list(session.scalars(query).all())


def link_encounter_vital(
    session: Session, encounter_id: int, link_data: EncounterVitalLinkCreate
) -> EncounterVital:
    encounter = session.scalar(
        select(Encounter).where(Encounter.id == encounter_id).with_for_update()
    )
    if encounter is None:
        raise HTTPException(status_code=404, detail="Visit note not found")
    if encounter.finalized_at is not None:
        raise HTTPException(
            status_code=409, detail="Finalized visit notes cannot change their vital links."
        )

    vital = session.scalar(
        select(Vital).where(Vital.id == link_data.vital_id).with_for_update()
    )
    if vital is None or vital.patient_id != encounter.patient_id:
        raise HTTPException(status_code=404, detail="Vitals record not found for this patient")
    if vital.recorded_on != encounter.visit_date:
        raise HTTPException(
            status_code=409, detail="Vitals must be recorded on the visit date."
        )

    existing = session.scalar(
        select(EncounterVital.id).where(
            EncounterVital.encounter_id == encounter_id,
            EncounterVital.vital_id == vital.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Vitals are already linked to this visit note.")

    snapshot = {
        f"{field}_at_link": getattr(vital, field) for field in SNAPSHOT_FIELDS
    }
    link = EncounterVital(encounter_id=encounter_id, vital_id=vital.id, **snapshot)
    session.add(link)
    session.flush()
    return link


def unlink_encounter_vital(session: Session, encounter_id: int, vital_id: int) -> None:
    encounter = session.scalar(
        select(Encounter).where(Encounter.id == encounter_id).with_for_update()
    )
    if encounter is None:
        raise HTTPException(status_code=404, detail="Visit note not found")
    if encounter.finalized_at is not None:
        raise HTTPException(
            status_code=409, detail="Finalized visit notes cannot change their vital links."
        )

    link = session.scalar(
        select(EncounterVital).where(
            EncounterVital.encounter_id == encounter_id,
            EncounterVital.vital_id == vital_id,
        )
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Vitals link not found")
    session.delete(link)
