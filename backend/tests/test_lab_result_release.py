"""Lab results must be released before appearing in the portal preview."""

import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.lab_orders import (
    list_portal_preview_lab_orders,
    read_lab_result,
    release_lab_result,
)
from backend.main import release_order_result
from backend.models import Base, Encounter, LabOrder, LabResult, Patient
from backend.schemas import LabResultRead


class LabResultReleaseTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patients = [
                Patient(
                    first_name=name, last_name="Example",
                    date_of_birth=date(1989, 3, 15), sex_at_birth="unknown",
                )
                for name in ("Avery", "Morgan")
            ]
            session.add_all(patients)
            session.flush()
            self.patient_id = patients[0].id
            finalized_at = datetime(2026, 11, 10, tzinfo=timezone.utc)
            visits = [
                Encounter(
                    patient_id=patient_id,
                    visit_date=date(2026, 11, 8),
                    reason_for_visit="Synthetic visit",
                    finalized_at=final_time,
                    assessment="Fictional signed assessment",
                )
                for patient_id, final_time in (
                    (self.patient_id, finalized_at),
                    (self.patient_id, None),
                    (patients[1].id, finalized_at),
                )
            ]
            session.add_all(visits)
            session.flush()
            orders = [
                LabOrder(
                    encounter_id=visit.id, test_name=name,
                    priority="routine", status=status,
                )
                for visit, name, status in (
                    (visits[0], "Synthetic CBC", "resulted"),
                    (visits[1], "Draft result", "resulted"),
                    (visits[2], "Other patient's result", "resulted"),
                    (visits[0], "Pending test", "ordered"),
                )
            ]
            session.add_all(orders)
            session.flush()
            self.result_order, self.draft_order, _, self.pending_order = [
                order.id for order in orders
            ]
            self.final_visit = visits[0].id
            for order in orders[:3]:
                session.add(LabResult(
                    lab_order_id=order.id,
                    collected_on=date(2026, 11, 8),
                    result_text=f"Private result for {order.test_name}",
                ))
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_unreleased_results_are_not_sent_to_portal(self):
        with Session(self.engine) as session:
            summaries = list_portal_preview_lab_orders(session, self.patient_id)
            self.assertEqual(
                {item.test_name for item in summaries},
                {"Synthetic CBC", "Pending test"},
            )
            self.assertIsNone(
                next(item for item in summaries if item.status == "resulted").result
            )
            self.assertNotIn("Private result", repr(summaries))
            self.assertIsNotNone(read_lab_result(session, self.result_order).result_text)

    def test_release_is_persistent_and_does_not_change_signed_note(self):
        with Session(self.engine) as session:
            released = release_lab_result(session, self.result_order)
            session.commit()
            self.assertIsNotNone(released.released_at)
            self.assertEqual(
                LabResultRead.model_validate(released).released_at,
                released.released_at,
            )

        with Session(self.engine) as session:
            summaries = list_portal_preview_lab_orders(session, self.patient_id)
            result = next(item for item in summaries if item.status == "resulted").result
            self.assertEqual(result.result_text, "Private result for Synthetic CBC")
            self.assertNotIn("released_at", result.model_dump())
            visit = session.get(Encounter, self.final_visit)
            self.assertEqual(visit.assessment, "Fictional signed assessment")
            self.assertIsNotNone(visit.finalized_at)
            with self.assertRaises(HTTPException) as raised:
                release_lab_result(session, self.result_order)
            self.assertEqual(raised.exception.status_code, 409)

    def test_draft_result_cannot_be_released(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                release_lab_result(session, self.draft_order)
            self.assertEqual(raised.exception.status_code, 409)
            self.assertIsNone(read_lab_result(session, self.draft_order).released_at)

    def test_missing_request_or_result_cannot_be_released(self):
        with Session(self.engine) as session:
            for order_id in (999999, self.pending_order):
                with self.assertRaises(HTTPException) as raised:
                    release_lab_result(session, order_id)
                self.assertEqual(raised.exception.status_code, 404)

    def test_endpoint_releases_result(self):
        with patch("backend.main.engine", self.engine):
            released = release_order_result(self.result_order)
        self.assertIsNotNone(released.released_at)


if __name__ == "__main__":
    unittest.main()
