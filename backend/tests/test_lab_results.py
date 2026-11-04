"""Lab results can arrive after a note is finalized without changing the note."""

import unittest
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.lab_orders import (
    create_lab_order,
    list_lab_orders,
    read_lab_result,
    record_lab_result,
)
from backend.models import Base, Encounter, LabResult, Patient
from backend.schemas import LabOrderCreate, LabOrderRead, LabResultCreate, LabResultRead


VISIT_DATE = date(2026, 10, 20)


class LabResultTests(unittest.TestCase):
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
                patient_id=patient.id, visit_date=VISIT_DATE,
                reason_for_visit="Synthetic checkup",
                assessment="Fictional assessment",
                plan="Follow-up planned",
            )
            final = Encounter(
                patient_id=patient.id, visit_date=VISIT_DATE,
                reason_for_visit="Synthetic follow-up",
                assessment="Fictional final assessment",
                plan="Existing plan",
                finalized_at=datetime.now(timezone.utc),
            )
            session.add_all([draft, final])
            session.flush()
            self.draft_id = draft.id
            self.final_id = final.id
            self.draft_order_id = create_lab_order(
                session, draft.id,
                LabOrderCreate(test_name="Fictional panel"),
            ).id
            # A finalized note can have a pre-existing order.
            from backend.models import LabOrder
            prior_order = LabOrder(
                encounter_id=final.id, test_name="Fictional test",
                priority="routine", status="ordered",
            )
            session.add(prior_order)
            session.flush()
            self.final_order_id = prior_order.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_result_is_permanent_and_marks_order_resulted(self):
        with Session(self.engine) as session:
            saved = record_lab_result(
                session, self.draft_order_id,
                LabResultCreate(
                    collected_on=VISIT_DATE,
                    result_text="  Fictional findings only.  ",
                ),
            )
            session.commit()
            session.refresh(saved)
            response = LabResultRead.model_validate(saved)
            self.assertEqual(response.result_text, "Fictional findings only.")
            self.assertEqual(response.collected_on, VISIT_DATE)
            self.assertIsNotNone(response.reported_at)
            self.assertEqual(response.lab_order_id, self.draft_order_id)
            self.assertEqual(
                LabOrderRead.model_validate(
                    list_lab_orders(session, self.draft_id)[0]
                ).status, "resulted",
            )

        with Session(self.engine) as session:
            self.assertEqual(
                read_lab_result(session, self.draft_order_id).result_text,
                "Fictional findings only.",
            )

    def test_result_arriving_after_finalization_preserves_signed_note(self):
        with Session(self.engine) as session:
            result = record_lab_result(
                session, self.final_order_id,
                LabResultCreate(
                    collected_on=VISIT_DATE,
                    result_text="Synthetic outside result",
                ),
            )
            session.commit()
            self.assertIsNotNone(result.id)

        with Session(self.engine) as session:
            note = session.get(Encounter, self.final_id)
            self.assertEqual(note.assessment, "Fictional final assessment")
            self.assertEqual(note.plan, "Existing plan")
            self.assertIsNotNone(note.finalized_at)
            self.assertEqual(
                read_lab_result(session, self.final_order_id).result_text,
                "Synthetic outside result",
            )

    def test_cannot_record_second_result(self):
        with Session(self.engine) as session:
            record_lab_result(
                session, self.draft_order_id,
                LabResultCreate(collected_on=VISIT_DATE, result_text="First"),
            )
            session.commit()

        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                record_lab_result(
                    session, self.draft_order_id,
                    LabResultCreate(collected_on=VISIT_DATE, result_text="Second"),
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(
                read_lab_result(session, self.draft_order_id).result_text,
                "First",
            )

    def test_collection_before_visit_rejected_without_changing_order(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                record_lab_result(
                    session, self.draft_order_id,
                    LabResultCreate(
                        collected_on=VISIT_DATE - timedelta(days=1),
                        result_text="Synthetic",
                    ),
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(list_lab_orders(session, self.draft_id)[0].status, "ordered")

    def test_missing_order_or_result_returns_404(self):
        with Session(self.engine) as session:
            for order_id in (9999, self.draft_order_id):
                with self.assertRaises(HTTPException) as raised:
                    read_lab_result(session, order_id)
                self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                record_lab_result(
                    session, 9999,
                    LabResultCreate(collected_on=VISIT_DATE, result_text="Synthetic"),
                )
            self.assertEqual(raised.exception.status_code, 404)

    def test_validation_rejects_blank_future_dates_and_client_status(self):
        for value in ("", "   ", "x" * 4001):
            with self.assertRaises(ValidationError):
                LabResultCreate(collected_on=VISIT_DATE, result_text=value)
        with self.assertRaises(ValidationError):
            LabResultCreate(
                collected_on=date.today() + timedelta(days=1),
                result_text="Synthetic",
            )
        with self.assertRaises(ValidationError):
            LabResultCreate.model_validate({
                "collected_on": VISIT_DATE,
                "result_text": "Synthetic",
                "lab_order_id": self.draft_order_id,
                "reported_at": "2026-11-03T00:00:00Z",
            })


if __name__ == "__main__":
    unittest.main()
