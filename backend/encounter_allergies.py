"""Preserve chart allergy details referenced by a visit note."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.encounters import lock_active_encounter
from backend.models import Encounter, EncounterAllergy, Allergy
from backend.schemas import EncounterAllergyLinkCreate


SNAPSHOT_FIELDS = (
    "allergen", "reaction", "severity", "status", "onset_date", "notes",
)


def list_encounter_allergies(session: Session, encounter_id: int) -> list[EncounterAllergy]:
    if session.get(Encounter, encounter_id) is None:
        raise HTTPException(status_code=404, detail="Visit note not found")

    query = (
        select(EncounterAllergy)
        .where(EncounterAllergy.encounter_id == encounter_id)
        .order_by(EncounterAllergy.id)
    )
    return list(session.scalars(query).all())


def link_encounter_allergy(
    session: Session, encounter_id: int, link_data: EncounterAllergyLinkCreate
) -> EncounterAllergy:
    encounter = lock_active_encounter(session, encounter_id)
    if encounter.finalized_at is not None:
        raise HTTPException(
            status_code=409, detail="Finalized visit notes cannot change their allergy links."
        )

    allergy = session.scalar(
        select(Allergy).where(Allergy.id == link_data.allergy_id).with_for_update()
    )
    if allergy is None or allergy.patient_id != encounter.patient_id:
        raise HTTPException(status_code=404, detail="Allergy not found for this patient")

    existing = session.scalar(
        select(EncounterAllergy.id).where(
            EncounterAllergy.encounter_id == encounter_id,
            EncounterAllergy.allergy_id == allergy.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Allergy is already linked to this visit note.")

    snapshot = {
        f"{field}_at_link": getattr(allergy, field) for field in SNAPSHOT_FIELDS
    }
    link = EncounterAllergy(
        encounter_id=encounter_id, allergy_id=allergy.id, **snapshot
    )
    session.add(link)
    session.flush()
    return link


def unlink_encounter_allergy(session: Session, encounter_id: int, allergy_id: int) -> None:
    encounter = lock_active_encounter(session, encounter_id)
    if encounter.finalized_at is not None:
        raise HTTPException(
            status_code=409, detail="Finalized visit notes cannot change their allergy links."
        )

    link = session.scalar(
        select(EncounterAllergy).where(
            EncounterAllergy.encounter_id == encounter_id,
            EncounterAllergy.allergy_id == allergy_id,
        )
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Allergy link not found")
    session.delete(link)
