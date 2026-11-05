"""Longitudinal lab requests and results remain tied to their source visits."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.lab_orders import (
    cancel_lab_order,
    create_lab_order,
    list_patient_lab_orders,
    record_lab_result,
)
from backend.main import read_patient_lab_orders
from backend.models import Base, Encounter, Patient
from backend.schemas import LabOrderCancel, LabOrderCreate, LabResultCreate


class PatientLabHistoryTests(unittest.TestCase):
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
            self.patient_id, self.other_id, self.empty_id = (
                patient.id for patient in patients
            )
            visits = [
                Encounter(
                    patient_id=patient_id, visit_date=visit_date,
                    reason_for_visit="Synthetic visit",
                )
                for patient_id, visit_date in (
                    (self.patient_id, date(2026, 10, 20)),
                    (self.patient_id, date(2026, 11, 2)),
                    (self.other_id, date(2026, 11, 3)),
                )
            ]
            session.add_all(visits)
            session.flush()
            self.old_visit, self.recent_visit, self.other_visit = (
                visit.id for visit in visits
            )
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_requests_across_visits_are_scoped_and_ordered(self):
        with Session(self.engine) as session:
            old = create_lab_order(
                session, self.old_visit, LabOrderCreate(test_name="Fictional CBC")
            )
            recent = create_lab_order(
                session, self.recent_visit, LabOrderCreate(test_name="Fictional CMP")
            )
            create_lab_order(
                session, self.other_visit, LabOrderCreate(test_name="Private example")
            )
            session.commit()
            rows = list_patient_lab_orders(session, self.patient_id)
            self.assertEqual([order.id for order, _, _ in rows], [recent.id, old.id])
            self.assertEqual(
                [visit_date for _, visit_date, _ in rows],
                [date(2026, 11, 2), date(2026, 10, 20)],
            )
            self.assertTrue(all(result is None for _, _, result in rows))
            self.assertEqual(len(list_patient_lab_orders(session, self.other_id)), 1)

    def test_completed_and_cancelled_requests_retain_context(self):
        with Session(self.engine) as session:
            old = create_lab_order(
                session, self.old_visit, LabOrderCreate(test_name="Fictional A1c")
            )
            recent = create_lab_order(
                session, self.recent_visit, LabOrderCreate(test_name="Fictional panel")
            )
            session.flush()
            note = session.get(Encounter, self.old_visit)
            note.finalized_at = datetime.now(timezone.utc)
            record_lab_result(
                session, old.id,
                LabResultCreate(
                    collected_on=date(2026, 10, 21),
                    result_text="Synthetic finding",
                ),
            )
            cancel_lab_order(
                session, recent.id,
                LabOrderCancel(reason="Synthetic duplicate request"),
            )
            session.commit()

        with patch("backend.main.engine", self.engine):
            response = read_patient_lab_orders(self.patient_id)

        self.assertEqual([item.status for item in response], ["cancelled", "resulted"])
        self.assertIsNone(response[0].result)
        self.assertEqual(response[0].cancellation_reason, "Synthetic duplicate request")
        self.assertEqual(response[1].result.result_text, "Synthetic finding")
        self.assertEqual(response[1].result.collected_on, date(2026, 10, 21))
        self.assertEqual(response[1].visit_date, date(2026, 10, 20))
        with Session(self.engine) as session:
            self.assertIsNotNone(session.get(Encounter, self.old_visit).finalized_at)

    def test_newest_request_first_for_same_visit_and_timestamps(self):
        with Session(self.engine) as session:
            first = create_lab_order(
                session, self.recent_visit, LabOrderCreate(test_name="Fictional first")
            )
            second = create_lab_order(
                session, self.recent_visit, LabOrderCreate(test_name="Fictional second")
            )
            third = create_lab_order(
                session, self.recent_visit, LabOrderCreate(test_name="Fictional third")
            )
            first.ordered_at = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
            second.ordered_at = first.ordered_at + timedelta(hours=1)
            third.ordered_at = second.ordered_at
            session.commit()
            self.assertEqual(
                [order.id for order, _, _ in
                 list_patient_lab_orders(session, self.patient_id)],
                [third.id, second.id, first.id],
            )

    def test_empty_history_and_missing_patient(self):
        with Session(self.engine) as session:
            self.assertEqual(list_patient_lab_orders(session, self.empty_id), [])
            with self.assertRaises(HTTPException) as missing:
                list_patient_lab_orders(session, 99999)
            self.assertEqual(missing.exception.status_code, 404)
        with patch("backend.main.engine", self.engine):
            self.assertEqual(read_patient_lab_orders(self.empty_id), [])
            with self.assertRaises(HTTPException) as missing:
                read_patient_lab_orders(99999)
            self.assertEqual(missing.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
