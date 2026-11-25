"""Patient-scoped selections for medications and laboratory orders.

Each association records the diagnosis name and code at selection. Later
changes to the problem list never rewrite a previous visit's indications.
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.icd10_catalog import RELEASE, lookup_code
from backend.models import Problem


def problem_values(payload, existing: Problem | None = None) -> dict:
    values = payload.model_dump(exclude={"icd10_code"})
    if "icd10_code" not in payload.model_fields_set and existing is not None:
        if existing.icd10_code and values["name"] != existing.name:
            raise HTTPException(status_code=422, detail="Confirm or change the diagnosis code when renaming a coded problem.")
        return values
    code = payload.icd10_code
    if code is None:
        return dict(values, icd10_code=None, icd10_title=None, icd10_release=None)
    # Retain an existing historical code and its version if explicitly unchanged.
    if existing is not None and code == existing.icd10_code and values["name"] == existing.name:
        return values
    selected = lookup_code(code)
    return dict(values, icd10_code=selected.code, icd10_title=selected.title, icd10_release=RELEASE)


def diagnosis_snapshot(problem: Problem) -> dict:
    return {
        "problem_id": problem.id,
        "problem_name": problem.name,
        "icd10_code": problem.icd10_code,
        "icd10_release": problem.icd10_release,
    }


def select_indications(session: Session, patient_id: int, ids: list[int], association_type):
    if len(ids) > 20 or any(value <= 0 for value in ids) or len(set(ids)) != len(ids):
        raise HTTPException(status_code=422, detail="Select up to 20 distinct chart problems.")
    if not ids:
        return []
    records = session.scalars(
        select(Problem).where(Problem.patient_id == patient_id, Problem.id.in_(ids))
        .order_by(Problem.id)
    ).all()
    if len(records) != len(ids):
        raise HTTPException(status_code=404, detail="A selected problem is not available in this chart.")
    return [association_type(**diagnosis_snapshot(problem)) for problem in records]


def replace_indications(session: Session, owner, patient_id: int, ids: list[int], association_type):
    # Validate the complete selection before making any changes. Keep a retained
    # association's original snapshot rather than rewriting historical context.
    selected = select_indications(session, patient_id, ids, association_type)
    existing = {link.problem_id: link for link in owner.indications}
    owner.indications = [existing.get(link.problem_id, link) for link in selected]
