"""Longitudinal care goals in a synthetic patient chart."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import CareGoal, CareGoalProgress, Patient
from backend.schemas import CareGoalComplete, CareGoalCreate, CareGoalProgressCreate


def list_care_goals(session: Session, patient_id: int) -> list[CareGoal]:
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    query = (
        select(CareGoal)
        .where(CareGoal.patient_id == patient_id)
        .order_by(CareGoal.created_at.desc(), CareGoal.id.desc())
    )
    return list(session.scalars(query).all())


def create_care_goal(
    session: Session, patient_id: int, goal_data: CareGoalCreate
) -> CareGoal:
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    goal = CareGoal(patient_id=patient_id, status="active", **goal_data.model_dump())
    session.add(goal)
    session.flush()
    return goal


def complete_care_goal(
    session: Session, goal_id: int, completion: CareGoalComplete
) -> CareGoal:
    goal = session.scalar(
        select(CareGoal).where(CareGoal.id == goal_id).with_for_update()
    )
    if goal is None:
        raise HTTPException(status_code=404, detail="Care goal not found")
    if goal.status != "active":
        raise HTTPException(status_code=409, detail="Only active care goals can be completed.")

    goal.status = "completed"
    goal.completed_at = datetime.now(timezone.utc)
    goal.completion_note = completion.completion_note
    session.flush()
    return goal

def list_goal_progress(session: Session, goal_id: int) -> list[CareGoalProgress]:
    if session.get(CareGoal, goal_id) is None:
        raise HTTPException(status_code=404, detail="Care goal not found")
    query = (
        select(CareGoalProgress)
        .where(CareGoalProgress.goal_id == goal_id)
        .order_by(CareGoalProgress.recorded_at, CareGoalProgress.id)
    )
    return list(session.scalars(query).all())


def record_goal_progress(
    session: Session, goal_id: int, progress_data: CareGoalProgressCreate
) -> CareGoalProgress:
    goal = session.scalar(select(CareGoal).where(CareGoal.id == goal_id).with_for_update())
    if goal is None:
        raise HTTPException(status_code=404, detail="Care goal not found")
    if goal.status != "active":
        raise HTTPException(status_code=409, detail="Only active care goals can receive progress notes.")

    entry = CareGoalProgress(goal_id=goal.id, note=progress_data.note)
    session.add(entry)
    session.flush()
    return entry
