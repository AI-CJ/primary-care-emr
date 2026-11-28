"""Small, current work-queue summaries without loading clinical records."""
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import (
    AppointmentChangeRequest, CareGoal, Encounter, FollowUpTask,
    LabOrder, LabResult, Patient, Referral,
)


class WorkQueueCounts(BaseModel):
    requests: int = Field(ge=0)
    results: int = Field(ge=0)
    followups: int = Field(ge=0)
    labs: int = Field(ge=0)
    referrals: int = Field(ge=0)
    goals: int = Field(ge=0)


def read_work_queue_counts(session: Session) -> WorkQueueCounts:
    """Use the worklists' status/archive rules in one aggregate SQL statement.

    Appointment requests are counted beyond the worklist's 100-row page. No
    chart fields or ORM collections are loaded, and no counts are cached.
    """
    active_chart = Patient.archived_at.is_(None)
    queries = {
        "requests": select(func.count(AppointmentChangeRequest.id))
        .join(Patient, Patient.id == AppointmentChangeRequest.patient_id)
        .where(AppointmentChangeRequest.status == "pending", active_chart),
        "results": select(func.count(LabOrder.id))
        .join(LabResult, LabResult.lab_order_id == LabOrder.id)
        .join(Encounter, Encounter.id == LabOrder.encounter_id)
        .join(Patient, Patient.id == Encounter.patient_id)
        .where(LabOrder.status == "resulted", LabResult.released_at.is_(None),
               Encounter.finalized_at.is_not(None), active_chart),
        "followups": select(func.count(FollowUpTask.id))
        .join(Patient, Patient.id == FollowUpTask.patient_id)
        .where(FollowUpTask.status == "open", active_chart),
        "labs": select(func.count(LabOrder.id))
        .join(Encounter, Encounter.id == LabOrder.encounter_id)
        .join(Patient, Patient.id == Encounter.patient_id)
        .where(LabOrder.status == "ordered", active_chart),
        "referrals": select(func.count(Referral.id))
        .join(Encounter, Encounter.id == Referral.encounter_id)
        .join(Patient, Patient.id == Encounter.patient_id)
        .where(Referral.status == "requested", active_chart),
        "goals": select(func.count(CareGoal.id))
        .join(Patient, Patient.id == CareGoal.patient_id)
        .where(CareGoal.status == "active", active_chart),
    }
    row = session.execute(select(*(
        query.scalar_subquery().label(name) for name, query in queries.items()
    ))).mappings().one()
    return WorkQueueCounts.model_validate(dict(row))
