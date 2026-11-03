"""Preserve chart medication details referenced by a visit note."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Encounter, EncounterMedication, Medication
from backend.schemas import EncounterMedicationLinkCreate


SNAPSHOT_FIELDS = (
    "name", "strength", "dose", "route", "frequency", "status",
    "start_date", "end_date", "instructions",
)


def list_encounter_medications(session: Session, encounter_id: int) -> list[EncounterMedication]:
    if session.get(Encounter, encounter_id) is None:
        raise HTTPException(status_code=404, detail="Visit note not found")

    query = (
        select(EncounterMedication)
        .where(EncounterMedication.encounter_id == encounter_id)
        .order_by(EncounterMedication.id)
    )
    return list(session.scalars(query).all())


def link_encounter_medication(
    session: Session, encounter_id: int, link_data: EncounterMedicationLinkCreate
) -> EncounterMedication:
    encounter = session.scalar(
        select(Encounter).where(Encounter.id == encounter_id).with_for_update()
    )
    if encounter is None:
        raise HTTPException(status_code=404, detail="Visit note not found")
    if encounter.finalized_at is not None:
        raise HTTPException(
            status_code=409, detail="Finalized visit notes cannot change their medication links."
        )

    medication = session.scalar(
        select(Medication).where(Medication.id == link_data.medication_id).with_for_update()
    )
    if medication is None or medication.patient_id != encounter.patient_id:
        raise HTTPException(status_code=404, detail="Medication not found for this patient")

    existing = session.scalar(
        select(EncounterMedication.id).where(
            EncounterMedication.encounter_id == encounter_id,
            EncounterMedication.medication_id == medication.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Medication is already linked to this visit note.")

    snapshot = {
        f"{field}_at_link": getattr(medication, field) for field in SNAPSHOT_FIELDS
    }
    link = EncounterMedication(
        encounter_id=encounter_id, medication_id=medication.id, **snapshot
    )
    session.add(link)
    session.flush()
    return link


def unlink_encounter_medication(session: Session, encounter_id: int, medication_id: int) -> None:
    encounter = session.scalar(
        select(Encounter).where(Encounter.id == encounter_id).with_for_update()
    )
    if encounter is None:
        raise HTTPException(status_code=404, detail="Visit note not found")
    if encounter.finalized_at is not None:
        raise HTTPException(
            status_code=409, detail="Finalized visit notes cannot change their medication links."
        )

    link = session.scalar(
        select(EncounterMedication).where(
            EncounterMedication.encounter_id == encounter_id,
            EncounterMedication.medication_id == medication_id,
        )
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Medication link not found")
    session.delete(link)
