"""Read-only clinical activity across a patient's chart."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import (
    CareGoal, Encounter, FollowUpTask, LabOrder, LabResult,
    Patient, Referral, Vital,
)
from backend.schemas import PatientTimelineEntry


def list_patient_timeline(
    session: Session, patient_id: int, limit: int = 50
) -> list[PatientTimelineEntry]:
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    entries: list[PatientTimelineEntry] = []

    for visit in session.scalars(
        select(Encounter).where(Encounter.patient_id == patient_id)
    ):
        entries.append(PatientTimelineEntry(
            kind="visit", record_id=visit.id, occurred_on=visit.visit_date,
            title=visit.reason_for_visit,
            status="finalized" if visit.finalized_at else "draft",
        ))

    for vital in session.scalars(
        select(Vital).where(Vital.patient_id == patient_id)
    ):
        entries.append(PatientTimelineEntry(
            kind="vitals", record_id=vital.id, occurred_on=vital.recorded_on,
            title="Vital signs recorded", status="recorded",
        ))

    orders = (
        select(LabOrder)
        .join(Encounter, LabOrder.encounter_id == Encounter.id)
        .where(Encounter.patient_id == patient_id)
    )
    for order in session.scalars(orders):
        entries.append(PatientTimelineEntry(
            kind="lab_order", record_id=order.id,
            occurred_on=order.ordered_at.date(), title=order.test_name,
            status=order.status,
        ))

    results = (
        select(LabResult, LabOrder)
        .join(LabOrder, LabResult.lab_order_id == LabOrder.id)
        .join(Encounter, LabOrder.encounter_id == Encounter.id)
        .where(Encounter.patient_id == patient_id)
    )
    for result, order in session.execute(results):
        entries.append(PatientTimelineEntry(
            kind="lab_result", record_id=result.id,
            occurred_on=result.reported_at.date(), title=order.test_name,
            status="reported",
        ))

    referrals = (
        select(Referral)
        .join(Encounter, Referral.encounter_id == Encounter.id)
        .where(Encounter.patient_id == patient_id)
    )
    for referral in session.scalars(referrals):
        entries.append(PatientTimelineEntry(
            kind="referral", record_id=referral.id,
            occurred_on=referral.requested_at.date(), title=referral.specialty,
            status=referral.status,
        ))

    for goal in session.scalars(
        select(CareGoal).where(CareGoal.patient_id == patient_id)
    ):
        entries.append(PatientTimelineEntry(
            kind="care_goal", record_id=goal.id,
            occurred_on=goal.created_at.date(), title=goal.title,
            status=goal.status,
        ))

    for task in session.scalars(
        select(FollowUpTask).where(FollowUpTask.patient_id == patient_id)
    ):
        entries.append(PatientTimelineEntry(
            kind="follow_up", record_id=task.id,
            occurred_on=task.created_at.date(), title=task.title,
            status=task.status,
        ))

    # This is a chart summary, not a record of every status change.
    entries.sort(
        key=lambda entry: (entry.occurred_on, entry.kind, entry.record_id),
        reverse=True,
    )
    return entries[:limit]
