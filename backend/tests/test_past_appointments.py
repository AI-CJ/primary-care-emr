"""Clinic worklist for appointments still open after their scheduled day."""

import unittest
from datetime import date, time
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.main import read_past_appointments
from backend.models import Appointment, Base, Patient
from backend.scheduling import list_past_appointments


class PastAppointmentsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.cutoff = date(2026, 11, 13)

        with Session(self.engine) as session:
            patients = [
                Patient(
                    first_name=name, last_name="Example",
                    date_of_birth=date(1990, 6, 12), sex_at_birth="unknown",
                )
                for name in ("Avery", "Morgan")
            ]
            session.add_all(patients)
            session.flush()
            self.patient_ids = [patient.id for patient in patients]

            appointments = [
                (0, date(2026, 11, 10), time(11), "scheduled"),
                (1, date(2026, 11, 10), time(9), "checked_in"),
                (0, date(2026, 11, 12), time(8), "scheduled"),
                (0, date(2026, 11, 12), time(9), "completed"),
                (0, date(2026, 11, 12), time(10), "cancelled"),
                (0, date(2026, 11, 12), time(11), "no_show"),
                (1, date(2026, 11, 13), time(8), "scheduled"),
                (1, date(2026, 11, 14), time(8), "checked_in"),
            ]
            session.add_all([
                Appointment(
                    patient_id=self.patient_ids[owner],
                    scheduled_date=day, start_time=start,
                    duration_minutes=30, reason_for_visit="Fictional visit",
                    status=status,
                )
                for owner, day, start, status in appointments
            ])
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_only_prior_unresolved_visits_in_oldest_first_order(self):
        with Session(self.engine) as session:
            records = list_past_appointments(session, self.cutoff)
        self.assertEqual(
            [(appointment.scheduled_date, appointment.start_time, appointment.status)
             for appointment, _ in records],
            [
                (date(2026, 11, 10), time(9), "checked_in"),
                (date(2026, 11, 10), time(11), "scheduled"),
                (date(2026, 11, 12), time(8), "scheduled"),
            ],
        )
        self.assertEqual(
            [patient.id for _, patient in records],
            [self.patient_ids[1], self.patient_ids[0], self.patient_ids[0]],
        )

    def test_no_visit_status_is_changed_by_review(self):
        with Session(self.engine) as session:
            before = list(session.scalars(select(Appointment).order_by(Appointment.id)))
            original = [(item.id, item.status) for item in before]
            list_past_appointments(session, self.cutoff)
            after = list(session.scalars(select(Appointment).order_by(Appointment.id)))
            self.assertEqual([(item.id, item.status) for item in after], original)

    def test_endpoint_uses_existing_schedule_response(self):
        with patch("backend.main.engine", self.engine):
            entries = read_past_appointments(self.cutoff)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].appointment.status, "checked_in")
        self.assertEqual(entries[0].patient.id, self.patient_ids[1])
        self.assertEqual(entries[0].patient.first_name, "Morgan")
        self.assertNotIn("sex_at_birth", entries[0].patient.model_dump())

    def test_cutoff_day_is_excluded(self):
        with Session(self.engine) as session:
            self.assertEqual(list_past_appointments(session, date(2026, 11, 10)), [])


if __name__ == "__main__":
    unittest.main()
