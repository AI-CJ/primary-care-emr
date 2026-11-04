"""Specialist referral requests recorded during a visit."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Encounter, Referral
from backend.schemas import ReferralCreate


def list_referrals(session: Session, encounter_id: int) -> list[Referral]:
    if session.get(Encounter, encounter_id) is None:
        raise HTTPException(status_code=404, detail="Visit note not found")

    query = (
        select(Referral)
        .where(Referral.encounter_id == encounter_id)
        .order_by(Referral.requested_at, Referral.id)
    )
    return list(session.scalars(query).all())


def create_referral(
    session: Session, encounter_id: int, referral_data: ReferralCreate
) -> Referral:
    # Prevent a referral from being added while the visit is being finalized.
    encounter = session.scalar(
        select(Encounter).where(Encounter.id == encounter_id).with_for_update()
    )
    if encounter is None:
        raise HTTPException(status_code=404, detail="Visit note not found")
    if encounter.finalized_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Referrals cannot be added to a finalized visit note.",
        )

    referral = Referral(
        encounter_id=encounter.id,
        status="requested",
        **referral_data.model_dump(),
    )
    session.add(referral)
    session.flush()
    return referral
