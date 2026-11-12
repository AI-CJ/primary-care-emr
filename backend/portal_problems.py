"""Patient-facing problem list for the staff portal preview."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Patient, Problem
from backend.schemas import PortalProblemSummary


def list_portal_preview_problems(
    session: Session, patient_id: int
) -> list[PortalProblemSummary]:
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    rows = session.execute(
        select(
            Problem.id,
            Problem.name,
            Problem.status,
            Problem.onset_date,
            Problem.resolved_date,
        )
        .where(Problem.patient_id == patient_id)
        .order_by(Problem.status, Problem.name, Problem.id)
    )
    return [
        PortalProblemSummary(
            id=problem_id,
            name=name,
            status=status,
            onset_date=onset_date,
            resolved_date=resolved_date,
        )
        for problem_id, name, status, onset_date, resolved_date in rows
    ]
