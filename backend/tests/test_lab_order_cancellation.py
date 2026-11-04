"""Pending lab requests can be cancelled without erasing their history."""

import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.lab_orders import (
    cancel_lab_order,
    create_lab_order,
    list_lab_orders,
    record_lab_result,
)
from backend.models import Base, Encounter, Patient
from backend.schemas import (
    LabOrderCancel, LabOrderCreate, LabOrderRead, LabResultCreate,
)


class LabOrderCancellationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Avery", last_name="Example",
                date_of_birth=date(1989, 3, 15), sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            draft = Encounter(
                patient_id=patient.id,
                visit_date=date(2026, 10, 20),
                reason_for_visit="Synthetic checkup",
            )
            signed = Encounter(
                patient_id=patient.id,
                visit_date=date(2026, 10, 20),
                reason_for_visit="Fictional follow-up",
                assessment="Signed assessment",
                finalized_at=datetime.now(timezone.utc),
            )
            session.add_all([draft, signed])
            session.flush()
            self.draft_id = draft.id
            self.signed_id = signed.id
            self.pending_id = create_lab_order(
                session, draft.id, LabOrderCreate(test_name="Fictional panel")
            ).id
            # The order was placed while the note was still a draft.
            from backend.models import LabOrder
            signed_order = LabOrder(
                encounter_id=signed.id,
                test_name="Fictional follow-up test",
                priority="routine",
                status="ordered",
            )
            session.add(signed_order)
            session.flush()
            self.signed_order_id = signed_order.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_cancellation_preserves_request_and_reason(self):
        with Session(self.engine) as session:
            cancelled = cancel_lab_order(
                session, self.pending_id,
                LabOrderCancel(reason="  Ordered in error.  "),
            )
            session.commit()
            data = LabOrderRead.model_validate(cancelled)
            self.assertEqual(data.status, "cancelled")
            self.assertEqual(data.cancellation_reason, "Ordered in error.")
            self.assertIsNotNone(data.cancelled_at)

        with Session(self.engine) as session:
            orders = list_lab_orders(session, self.draft_id)
            self.assertEqual(len(orders), 1)
            self.assertEqual(orders[0].test_name, "Fictional panel")
            self.assertEqual(orders[0].status, "cancelled")
            self.assertEqual(orders[0].cancellation_reason, "Ordered in error.")

    def test_cannot_cancel_twice_or_record_result_after_cancellation(self):
        with Session(self.engine) as session:
            cancel_lab_order(
                session, self.pending_id, LabOrderCancel(reason="Not needed")
            )
            session.commit()
        with Session(self.engine) as session:
            for operation in (
                lambda: cancel_lab_order(
                    session, self.pending_id, LabOrderCancel(reason="Again")
                ),
                lambda: record_lab_result(
                    session, self.pending_id,
                    LabResultCreate(
                        collected_on=date(2026, 10, 20),
                        result_text="Synthetic result",
                    ),
                ),
            ):
                with self.assertRaises(HTTPException) as raised:
                    operation()
                self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(
                list_lab_orders(session, self.draft_id)[0].cancellation_reason,
                "Not needed",
            )

    def test_resulted_request_cannot_be_cancelled(self):
        with Session(self.engine) as session:
            record_lab_result(
                session, self.pending_id,
                LabResultCreate(
                    collected_on=date(2026, 10, 20),
                    result_text="Synthetic result",
                ),
            )
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                cancel_lab_order(
                    session, self.pending_id, LabOrderCancel(reason="Too late")
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(list_lab_orders(session, self.draft_id)[0].status, "resulted")

    def test_pending_request_can_be_cancelled_after_note_finalization(self):
        with Session(self.engine) as session:
            cancel_lab_order(
                session, self.signed_order_id,
                LabOrderCancel(reason="Patient declined fictional test"),
            )
            session.commit()
            note = session.get(Encounter, self.signed_id)
            self.assertEqual(note.assessment, "Signed assessment")
            self.assertIsNotNone(note.finalized_at)
            self.assertEqual(list_lab_orders(session, self.signed_id)[0].status, "cancelled")

    def test_missing_order_returns_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                cancel_lab_order(session, 9999, LabOrderCancel(reason="Not found"))
            self.assertEqual(raised.exception.status_code, 404)

    def test_cancellation_requires_a_reason_and_rejects_extra_fields(self):
        for reason in ("", "  ", "x" * 1001):
            with self.assertRaises(ValidationError):
                LabOrderCancel(reason=reason)
        with self.assertRaises(ValidationError):
            LabOrderCancel.model_validate({
                "reason": "Not needed", "status": "cancelled",
            })


if __name__ == "__main__":
    unittest.main()
