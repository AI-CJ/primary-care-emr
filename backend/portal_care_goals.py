"""Care goal summaries for the staff portal preview."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import CareGoal, Patient
from backend.schemas import PortalCareGoalSummary


def list_portal_preview_care_goals(
    session: Session, patient_id: int
) -> list[PortalCareGoalSummary]:
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    rows = session.execute(
        select(
            CareGoal.id,
            CareGoal.title,
            CareGoal.target_date,
            CareGoal.status,
            CareGoal.created_at,
            CareGoal.completed_at,
            CareGoal.discontinued_at,
        )
        .where(CareGoal.patient_id == patient_id)
        .order_by(CareGoal.created_at.desc(), CareGoal.id.desc())
    )
    return [
        PortalCareGoalSummary(
            id=goal_id,
            title=title,
            target_date=target_date,
            status=status,
            created_at=created_at,
            completed_at=completed_at,
            discontinued_at=discontinued_at,
        )
        for (
            goal_id, title, target_date, status, created_at,
            completed_at, discontinued_at,
        ) in rows
    ]
