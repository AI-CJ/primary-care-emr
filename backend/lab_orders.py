"""Lab test requests associated with a visit note."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Encounter, LabOrder, LabResult
from backend.schemas import LabOrderCancel, LabOrderCreate, LabResultCreate


def list_lab_orders(session: Session, encounter_id: int) -> list[LabOrder]:
    if session.get(Encounter, encounter_id) is None:
        raise HTTPException(status_code=404, detail="Visit note not found")

    query = (
        select(LabOrder)
        .where(LabOrder.encounter_id == encounter_id)
        .order_by(LabOrder.ordered_at, LabOrder.id)
    )
    return list(session.scalars(query).all())


def create_lab_order(
    session: Session, encounter_id: int, order_data: LabOrderCreate
) -> LabOrder:
    # Serializes order placement with note finalization.
    encounter = session.scalar(
        select(Encounter).where(Encounter.id == encounter_id).with_for_update()
    )
    if encounter is None:
        raise HTTPException(status_code=404, detail="Visit note not found")
    if encounter.finalized_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Lab orders cannot be added to a finalized visit note.",
        )

    order = LabOrder(
        encounter_id=encounter.id,
        status="ordered",
        **order_data.model_dump(),
    )
    session.add(order)
    session.flush()
    return order


def cancel_lab_order(
    session: Session, order_id: int, cancellation: LabOrderCancel
) -> LabOrder:
    order = session.scalar(
        select(LabOrder).where(LabOrder.id == order_id).with_for_update()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Lab request not found")
    if order.status != "ordered":
        raise HTTPException(
            status_code=409, detail="Only pending lab requests can be cancelled."
        )

    order.status = "cancelled"
    order.cancelled_at = datetime.now(timezone.utc)
    order.cancellation_reason = cancellation.reason
    session.flush()
    return order


def read_lab_result(session: Session, order_id: int) -> LabResult:
    if session.get(LabOrder, order_id) is None:
        raise HTTPException(status_code=404, detail="Lab request not found")

    result = session.scalar(
        select(LabResult).where(LabResult.lab_order_id == order_id)
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Lab result not found")
    return result


def record_lab_result(
    session: Session, order_id: int, result_data: LabResultCreate
) -> LabResult:
    # One result per request; the row lock also prevents duplicate concurrent entries.
    order = session.scalar(
        select(LabOrder).where(LabOrder.id == order_id).with_for_update()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Lab request not found")
    if order.status != "ordered":
        raise HTTPException(status_code=409, detail="Lab request already has a result.")

    encounter = session.get(Encounter, order.encounter_id)
    if result_data.collected_on < encounter.visit_date:
        raise HTTPException(
            status_code=409,
            detail="Collection date cannot precede the visit.",
        )

    result = LabResult(
        lab_order_id=order.id, **result_data.model_dump()
    )
    session.add(result)
    order.status = "resulted"
    session.flush()
    return result
