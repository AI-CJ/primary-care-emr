"""Patient-specific staff follow-up tasks for the synthetic clinic."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import CareGoal, FollowUpDueDateChange, FollowUpTask, Patient
from backend.schemas import (
    FollowUpTaskCancel,
    FollowUpTaskComplete,
    FollowUpTaskCreate,
    FollowUpTaskReschedule,
)


def list_follow_up_tasks(session: Session, patient_id: int) -> list[FollowUpTask]:
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    query = (
        select(FollowUpTask)
        .where(FollowUpTask.patient_id == patient_id)
        .order_by(FollowUpTask.created_at.desc(), FollowUpTask.id.desc())
    )
    return list(session.scalars(query).all())

    
def list_open_follow_up_tasks(session: Session) -> list[tuple[FollowUpTask, Patient]]:
    """Open follow-up tasks across the clinic, nearest due dates first."""
    query = (
        select(FollowUpTask, Patient)
        .join(Patient, FollowUpTask.patient_id == Patient.id)
        .where(FollowUpTask.status == "open")
        .order_by(
            FollowUpTask.due_date.is_(None),
            FollowUpTask.due_date,
            FollowUpTask.created_at,
            FollowUpTask.id,
        )
    )
    return list(session.execute(query).all())

def create_follow_up_task(
    session: Session, patient_id: int, task_data: FollowUpTaskCreate
) -> FollowUpTask:
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    if task_data.care_goal_id is not None:
        goal = session.scalar(
            select(CareGoal)
            .where(
                CareGoal.id == task_data.care_goal_id,
                CareGoal.patient_id == patient_id,
            )
            .with_for_update()
        )
        if goal is None:
            raise HTTPException(status_code=404, detail="Care goal not found for patient")
        if goal.status != "active":
            raise HTTPException(
                status_code=409,
                detail="Only active care goals can have new follow-up tasks.",
            )

    task = FollowUpTask(patient_id=patient_id, status="open", **task_data.model_dump())
    session.add(task)
    session.flush()
    return task


def complete_follow_up_task(
    session: Session, task_id: int, completion: FollowUpTaskComplete
) -> FollowUpTask:
    task = session.scalar(
        select(FollowUpTask).where(FollowUpTask.id == task_id).with_for_update()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Follow-up task not found")
    if task.status != "open":
        raise HTTPException(status_code=409, detail="Only open tasks can be completed.")

    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)
    task.completion_note = completion.completion_note
    session.flush()
    return task


def cancel_follow_up_task(
    session: Session, task_id: int, cancellation: FollowUpTaskCancel
) -> FollowUpTask:
    task = session.scalar(
        select(FollowUpTask).where(FollowUpTask.id == task_id).with_for_update()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Follow-up task not found")
    if task.status != "open":
        raise HTTPException(status_code=409, detail="Only open tasks can be cancelled.")

    task.status = "cancelled"
    task.cancelled_at = datetime.now(timezone.utc)
    task.cancellation_reason = cancellation.reason
    session.flush()
    return task


def reschedule_follow_up_task(
    session: Session, task_id: int, change: FollowUpTaskReschedule
) -> FollowUpTask:
    task = session.scalar(
        select(FollowUpTask).where(FollowUpTask.id == task_id).with_for_update()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Follow-up task not found")
    if task.status != "open":
        raise HTTPException(status_code=409, detail="Only open tasks can be rescheduled.")
    if task.due_date == change.due_date:
        raise HTTPException(status_code=409, detail="Due date has not changed.")

    session.add(FollowUpDueDateChange(
        task_id=task.id,
        previous_due_date=task.due_date,
        new_due_date=change.due_date,
        reason=change.reason,
    ))
    task.due_date = change.due_date
    session.flush()
    return task


def list_follow_up_due_date_changes(
    session: Session, task_id: int
) -> list[FollowUpDueDateChange]:
    if session.get(FollowUpTask, task_id) is None:
        raise HTTPException(status_code=404, detail="Follow-up task not found")
    query = (
        select(FollowUpDueDateChange)
        .where(FollowUpDueDateChange.task_id == task_id)
        .order_by(FollowUpDueDateChange.changed_at, FollowUpDueDateChange.id)
    )
    return list(session.scalars(query).all())
