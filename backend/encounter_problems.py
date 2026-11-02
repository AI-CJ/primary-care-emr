"""Associate chart problems with draft visit notes."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Encounter, EncounterProblem, Problem
from backend.schemas import EncounterProblemLinkCreate


def list_encounter_problems(session: Session, encounter_id: int) -> list[EncounterProblem]:
    if session.get(Encounter, encounter_id) is None:
        raise HTTPException(status_code=404, detail="Visit note not found")

    query = (
        select(EncounterProblem)
        .where(EncounterProblem.encounter_id == encounter_id)
        .order_by(EncounterProblem.id)
    )
    return list(session.scalars(query).all())


def link_encounter_problem(
    session: Session, encounter_id: int, link_data: EncounterProblemLinkCreate
) -> EncounterProblem:
    encounter = session.scalar(
        select(Encounter).where(Encounter.id == encounter_id).with_for_update()
    )
    if encounter is None:
        raise HTTPException(status_code=404, detail="Visit note not found")
    if encounter.finalized_at is not None:
        raise HTTPException(
            status_code=409, detail="Finalized visit notes cannot change their problem links."
        )

    problem = session.get(Problem, link_data.problem_id)
    if problem is None or problem.patient_id != encounter.patient_id:
        raise HTTPException(status_code=404, detail="Problem not found for this patient")

    existing = session.scalar(
        select(EncounterProblem.id).where(
            EncounterProblem.encounter_id == encounter_id,
            EncounterProblem.problem_id == problem.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Problem is already linked to this visit note.")

    link = EncounterProblem(
        encounter_id=encounter_id,
        problem_id=problem.id,
        problem_name_at_link=problem.name,
        problem_status_at_link=problem.status,
    )
    session.add(link)
    session.flush()
    return link


def unlink_encounter_problem(
    session: Session, encounter_id: int, problem_id: int
) -> None:
    encounter = session.scalar(
        select(Encounter).where(Encounter.id == encounter_id).with_for_update()
    )
    if encounter is None:
        raise HTTPException(status_code=404, detail="Visit note not found")
    if encounter.finalized_at is not None:
        raise HTTPException(
            status_code=409, detail="Finalized visit notes cannot change their problem links."
        )

    link = session.scalar(
        select(EncounterProblem).where(
            EncounterProblem.encounter_id == encounter_id,
            EncounterProblem.problem_id == problem_id,
        )
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Problem link not found")
    session.delete(link)
