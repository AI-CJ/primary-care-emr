"""Lab test requests associated with a visit note."""

from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from backend.models import Encounter, LabOrder, LabResult, Patient
from backend.schemas import (
    LabOrderCancel, LabOrderCreate, LabResultCreate,
    PortalLabOrderSummary, PortalLabResultSummary,
)


def list_lab_orders(session: Session, encounter_id: int) -> list[LabOrder]:
    if session.get(Encounter, encounter_id) is None:
        raise HTTPException(status_code=404, detail="Visit note not found")

    query = (
        select(LabOrder)
        .where(LabOrder.encounter_id == encounter_id)
        .order_by(LabOrder.ordered_at, LabOrder.id)
    )
    return list(session.scalars(query).all())



def list_patient_lab_orders(
    session: Session, patient_id: int
) -> list[tuple[LabOrder, date, LabResult | None]]:
    """Return all lab requests and available results across a patient's visits."""
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    query = (
        select(LabOrder, Encounter.visit_date, LabResult)
        .join(Encounter, LabOrder.encounter_id == Encounter.id)
        .outerjoin(LabResult, LabResult.lab_order_id == LabOrder.id)
        .where(Encounter.patient_id == patient_id)
        .order_by(
            Encounter.visit_date.desc(),
            LabOrder.ordered_at.desc(),
            LabOrder.id.desc(),
        )
    )
    return list(session.execute(query).all())




def list_portal_preview_lab_orders(
    session: Session, patient_id: int
) -> list[PortalLabOrderSummary]:
    """Show lab requests from finalized visits without staff-only fields."""
    if session.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    rows = session.execute(
        select(
            LabOrder.id,
            LabOrder.test_name,
            LabOrder.status,
            LabOrder.ordered_at,
            LabOrder.cancelled_at,
            LabResult.collected_on,
            LabResult.reported_at,
            LabResult.result_text,
            LabResult.released_at,
        )
        .join(Encounter, LabOrder.encounter_id == Encounter.id)
        .outerjoin(LabResult, LabResult.lab_order_id == LabOrder.id)
        .where(Encounter.patient_id == patient_id, Encounter.finalized_at.is_not(None))
        .order_by(
            Encounter.visit_date.desc(),
            LabOrder.ordered_at.desc(),
            LabOrder.id.desc(),
        )
    )
    return [
        PortalLabOrderSummary(
            id=order_id,
            test_name=test_name,
            status=status,
            ordered_at=ordered_at,
            cancelled_at=cancelled_at,
            result=PortalLabResultSummary(
                collected_on=collected_on,
                reported_at=reported_at,
                result_text=result_text,
            ) if released_at is not None else None,
        )
        for (
            order_id, test_name, status, ordered_at, cancelled_at,
            collected_on, reported_at, result_text, released_at,
        ) in rows
    ]


def list_pending_lab_orders(
    session: Session,
) -> list[tuple[LabOrder, date, Patient]]:
    """Outstanding orders for the clinic worklist, oldest first within priority."""
    query = (
        select(LabOrder, Encounter.visit_date, Patient)
        .join(Encounter, LabOrder.encounter_id == Encounter.id)
        .join(Patient, Encounter.patient_id == Patient.id)
        .where(LabOrder.status == "ordered")
        .order_by(
            case((LabOrder.priority == "urgent", 0), else_=1),
            LabOrder.ordered_at,
            LabOrder.id,
        )
    )
    return list(session.execute(query).all())


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


def release_lab_result(session: Session, order_id: int) -> LabResult:
    # Use the same order lock as result recording.
    order = session.scalar(
        select(LabOrder).where(LabOrder.id == order_id).with_for_update()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Lab request not found")

    result = session.scalar(
        select(LabResult).where(LabResult.lab_order_id == order_id)
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Lab result not found")

    encounter = session.get(Encounter, order.encounter_id)
    if encounter.finalized_at is None:
        raise HTTPException(
            status_code=409, detail="Finalize the visit before releasing lab results."
        )
    if result.released_at is not None:
        raise HTTPException(status_code=409, detail="Lab result already released.")

    result.released_at = datetime.now(timezone.utc)
    session.flush()
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
