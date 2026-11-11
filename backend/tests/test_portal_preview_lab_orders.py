"""Portal lab preview excludes draft visits and internal order details."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.lab_orders import list_portal_preview_lab_orders
from backend.main import read_portal_preview_lab_orders
from backend.models import Base, Encounter, LabOrder, LabResult, Patient


class PortalPreviewLabOrderTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            patients = [
                Patient(
                    first_name=first, last_name="Example",
                    date_of_birth=date(1991, 3, 8), sex_at_birth="unknown",
                )
                for first in ("Avery", "Morgan", "Taylor")
            ]
            session.add_all(patients)
            session.flush()
            self.patient_id, other_id, self.empty_id = [item.id for item in patients]
            final_at = datetime(2026, 11, 8, tzinfo=timezone.utc)
            visits = [
                Encounter(
                    patient_id=patient_id, visit_date=visit_date,
                    reason_for_visit="Private synthetic visit",
                    finalized_at=finalized_at,
                )
                for patient_id, visit_date, finalized_at in (
                    (self.patient_id, date(2026, 10, 20), final_at),
                    (self.patient_id, date(2026, 11, 5), final_at),
                    (self.patient_id, date(2026, 11, 7), None),
                    (other_id, date(2026, 11, 9), final_at),
                )
            ]
            session.add_all(visits)
            session.flush()

            base = datetime(2026, 11, 5, 9, tzinfo=timezone.utc)
            orders = [
                LabOrder(
                    encounter_id=visits[0].id, test_name="Fictional A1c",
                    priority="routine", clinical_reason="Private clinical reason",
                    status="resulted", ordered_at=base,
                ),
                LabOrder(
                    encounter_id=visits[1].id, test_name="Fictional CBC",
                    priority="urgent", status="ordered", ordered_at=base + timedelta(hours=1),
                ),
                LabOrder(
                    encounter_id=visits[1].id, test_name="Fictional CMP",
                    priority="routine", status="cancelled", ordered_at=base + timedelta(hours=1),
                    cancelled_at=base + timedelta(hours=2),
                    cancellation_reason="Private cancellation reason",
                ),
                LabOrder(
                    encounter_id=visits[2].id, test_name="Unreleased draft request",
                    priority="urgent", status="ordered", ordered_at=base + timedelta(days=1),
                ),
                LabOrder(
                    encounter_id=visits[3].id, test_name="Other patient request",
                    priority="urgent", status="ordered", ordered_at=base + timedelta(days=2),
                ),
            ]
            session.add_all(orders)
            session.flush()
            session.add(LabResult(
                lab_order_id=orders[0].id,
                collected_on=date(2026, 10, 21),
                result_text="Fictional result for preview",
                reported_at=base + timedelta(days=2),
            ))
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_only_finalized_patient_orders_in_stable_order(self):
        with Session(self.engine) as session:
            summaries = list_portal_preview_lab_orders(session, self.patient_id)

        self.assertEqual(
            [item.test_name for item in summaries],
            ["Fictional CMP", "Fictional CBC", "Fictional A1c"],
        )
        self.assertEqual(
            [item.status for item in summaries],
            ["cancelled", "ordered", "resulted"],
        )
        self.assertIsNone(summaries[0].result)
        self.assertIsNone(summaries[1].result)
        self.assertEqual(summaries[2].result.result_text, "Fictional result for preview")
        self.assertEqual(summaries[2].result.collected_on, date(2026, 10, 21))

    def test_response_excludes_staff_only_fields(self):
        with patch("backend.main.engine", self.engine):
            summaries = read_portal_preview_lab_orders(self.patient_id)

        allowed = {
            "id", "test_name", "status", "ordered_at", "cancelled_at", "result"
        }
        for item in summaries:
            self.assertEqual(set(item.model_dump(mode="json")), allowed)
        self.assertEqual(
            set(summaries[2].result.model_dump(mode="json")),
            {"collected_on", "result_text", "reported_at"},
        )
        serialized = repr(summaries)
        for secret in (
            "Private", "Unreleased draft request", "Other patient request"
        ):
            self.assertNotIn(secret, serialized)

    def test_empty_chart_and_missing_patient(self):
        with Session(self.engine) as session:
            self.assertEqual(list_portal_preview_lab_orders(session, self.empty_id), [])
            with self.assertRaises(HTTPException) as raised:
                list_portal_preview_lab_orders(session, 999999)
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
