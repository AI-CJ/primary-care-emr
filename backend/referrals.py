"""Specialist referral requests recorded during a visit."""

from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Encounter, Patient, Referral
from backend.schemas import ReferralCancel, ReferralComplete, ReferralCreate


def list_referrals(session: Session, encounter_id: int) -> list[Referral]:
    if session.get(Encounter, encounter_id) is None:
        raise HTTPException(status_code=404, detail="Visit note not found")

    query = (
        select(Referral)
        .where(Referral.encounter_id == encounter_id)
        .order_by(Referral.requested_at, Referral.id)
    )
    return list(session.scalars(query).all())


def list_patient_referrals(
    session: Session, patient_id: int
) -> list[tuple[Referral, date]]:
    """Return referrals from all visits in one patient's chart."""
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    query = (
        select(Referral, Encounter.visit_date)
        .join(Encounter, Referral.encounter_id == Encounter.id)
        .where(Encounter.patient_id == patient_id)
        .order_by(
            Encounter.visit_date.desc(),
            Referral.requested_at.desc(),
            Referral.id.desc(),
        )
    )
    return list(session.execute(query).all())


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


def cancel_referral(
    session: Session, referral_id: int, cancellation: ReferralCancel
) -> Referral:
    referral = session.scalar(
        select(Referral).where(Referral.id == referral_id).with_for_update()
    )
    if referral is None:
        raise HTTPException(status_code=404, detail="Referral request not found")
    if referral.status != "requested":
        raise HTTPException(
            status_code=409, detail="Only pending referral requests can be cancelled."
        )

    # A pending request may be withdrawn after its visit note is finalized.
    referral.status = "cancelled"
    referral.cancelled_at = datetime.now(timezone.utc)
    referral.cancellation_reason = cancellation.reason
    session.flush()
    return referral


def complete_referral(
    session: Session, referral_id: int, follow_up: ReferralComplete
) -> Referral:
    referral = session.scalar(
        select(Referral).where(Referral.id == referral_id).with_for_update()
    )
    if referral is None:
        raise HTTPException(status_code=404, detail="Referral request not found")
    if referral.status != "requested":
        raise HTTPException(
            status_code=409, detail="Only pending referrals can be completed."
        )

    encounter = session.get(Encounter, referral.encounter_id)
    if follow_up.seen_on < encounter.visit_date:
        raise HTTPException(
            status_code=409,
            detail="Specialist visit date cannot precede the referring visit.",
        )

    # Follow-up can be recorded after the original visit note is finalized.
    referral.status = "completed"
    referral.completed_at = datetime.now(timezone.utc)
    referral.seen_on = follow_up.seen_on
    referral.follow_up_summary = follow_up.follow_up_summary
    session.flush()
    return referral
