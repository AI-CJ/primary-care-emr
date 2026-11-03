"""Lab requests remain attached to a visit and do not rewrite finalized notes."""

import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.lab_orders import create_lab_order, list_lab_orders
from backend.models import Base, Encounter, Patient
from backend.schemas import LabOrderCreate, LabOrderRead


class LabOrderTests(unittest.TestCase):
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
                patient_id=patient.id, visit_date=date(2026, 11, 2),
                reason_for_visit="Synthetic checkup",
            )
            final = Encounter(
                patient_id=patient.id, visit_date=date(2026, 11, 1),
                reason_for_visit="Synthetic follow-up",
                finalized_at=datetime.now(timezone.utc),
            )
            session.add_all([draft, final])
            session.flush()
            self.draft_id = draft.id
            self.final_id = final.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_places_and_lists_order_for_draft_visit(self):
        with Session(self.engine) as session:
            order = create_lab_order(
                session, self.draft_id,
                LabOrderCreate(
                    test_name="  Fictional blood panel  ",
                    priority="routine",
                    clinical_reason="  Synthetic screening  ",
                ),
            )
            session.commit()
            session.refresh(order)
            saved = LabOrderRead.model_validate(order)
            self.assertEqual(saved.encounter_id, self.draft_id)
            self.assertEqual(saved.test_name, "Fictional blood panel")
            self.assertEqual(saved.clinical_reason, "Synthetic screening")
            self.assertEqual(saved.status, "ordered")
            self.assertIsNotNone(saved.ordered_at)

        with Session(self.engine) as session:
            orders = list_lab_orders(session, self.draft_id)
            self.assertEqual(len(orders), 1)
            self.assertEqual(orders[0].test_name, "Fictional blood panel")
            self.assertEqual(list_lab_orders(session, self.final_id), [])

    def test_multiple_orders_are_kept_separately(self):
        with Session(self.engine) as session:
            create_lab_order(session, self.draft_id, LabOrderCreate(test_name="Fictional test A"))
            create_lab_order(
                session, self.draft_id,
                LabOrderCreate(test_name="Fictional test B", priority="urgent"),
            )
            session.commit()

        with Session(self.engine) as session:
            orders = list_lab_orders(session, self.draft_id)
            self.assertEqual([order.test_name for order in orders], [
                "Fictional test A", "Fictional test B",
            ])
            self.assertEqual(orders[1].priority, "urgent")

    def test_cannot_add_order_to_finalized_note(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_lab_order(session, self.final_id, LabOrderCreate(test_name="Test"))
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(list_lab_orders(session, self.final_id), [])

    def test_missing_note_returns_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_lab_order(session, 9999, LabOrderCreate(test_name="Test"))
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                list_lab_orders(session, 9999)
            self.assertEqual(raised.exception.status_code, 404)

    def test_validation_rejects_bad_names_priorities_and_extra_data(self):
        for value in ("", "  ", "X" * 201):
            with self.assertRaises(ValidationError):
                LabOrderCreate(test_name=value)
        with self.assertRaises(ValidationError):
            LabOrderCreate(test_name="Test", priority="stat")
        with self.assertRaises(ValidationError):
            LabOrderCreate(test_name="Test", clinical_reason="x" * 1001)
        with self.assertRaises(ValidationError):
            LabOrderCreate.model_validate({
                "test_name": "Test", "status": "completed",
            })


if __name__ == "__main__":
    unittest.main()
