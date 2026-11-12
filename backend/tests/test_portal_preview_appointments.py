"""The portal preview exposes appointment dates and statuses, not staff fields."""

import unittest
from datetime import date, time
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.main import read_portal_preview_appointments
from backend.models import Appointment, Base, Patient
from backend.portal_appointments import list_portal_preview_appointments


class PortalPreviewAppointmentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patients = [
                Patient(
                    first_name=name, last_name="Example",
                    date_of_birth=date(1990, 6, 12), sex_at_birth="unknown",
                )
                for name in ("Avery", "Morgan", "Taylor")
            ]
            session.add_all(patients)
            session.flush()
            self.patient_id, other_id, self.empty_id = [p.id for p in patients]
            session.add_all([
                Appointment(
                    patient_id=self.patient_id, scheduled_date=date(2026, 11, 15),
                    start_time=time(14, 30), duration_minutes=60,
                    reason_for_visit="Fictional follow-up", status="scheduled",
                ),
                Appointment(
                    patient_id=self.patient_id, scheduled_date=date(2026, 10, 10),
                    start_time=time(9, 0), duration_minutes=30,
                    reason_for_visit="Fictional prior visit", status="completed",
                ),
                Appointment(
                    patient_id=self.patient_id, scheduled_date=date(2026, 10, 10),
                    start_time=time(9, 0), duration_minutes=45,
                    reason_for_visit="Fictional missed visit", status="no_show",
                ),
                Appointment(
                    patient_id=self.patient_id, scheduled_date=date(2026, 9, 1),
                    start_time=time(11, 0), duration_minutes=30,
                    reason_for_visit="Fictional cancelled visit", status="cancelled",
                ),
                Appointment(
                    patient_id=other_id, scheduled_date=date(2026, 12, 1),
                    start_time=time(8, 0), duration_minutes=180,
                    reason_for_visit="Other patient's visit", status="scheduled",
                ),
            ])
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_appointments_keep_status_history_and_order(self):
        with Session(self.engine) as session:
            appointments = list_portal_preview_appointments(session, self.patient_id)

        self.assertEqual(
            [appointment.reason_for_visit for appointment in appointments],
            [
                "Fictional follow-up", "Fictional missed visit",
                "Fictional prior visit", "Fictional cancelled visit",
            ],
        )
        self.assertEqual(
            [appointment.status for appointment in appointments],
            ["scheduled", "no_show", "completed", "cancelled"],
        )
        self.assertEqual(appointments[0].start_time, time(14, 30))

    def test_response_does_not_include_staff_fields_or_other_patients(self):
        with Session(self.engine) as session:
            appointments = list_portal_preview_appointments(session, self.patient_id)

        expected = {
            "id", "scheduled_date", "start_time", "reason_for_visit", "status",
        }
        for appointment in appointments:
            self.assertEqual(set(appointment.model_dump(mode="json")), expected)
        serialized = repr(appointments)
        self.assertNotIn("Other patient's visit", serialized)
        self.assertNotIn("patient_id=", serialized)
        self.assertNotIn("duration_minutes=", serialized)

    def test_endpoint_returns_portal_summary(self):
        with patch("backend.main.engine", self.engine):
            appointments = read_portal_preview_appointments(self.patient_id)
        self.assertEqual(len(appointments), 4)
        self.assertEqual(appointments[0].reason_for_visit, "Fictional follow-up")

    def test_empty_chart_and_missing_patient(self):
        with Session(self.engine) as session:
            self.assertEqual(
                list_portal_preview_appointments(session, self.empty_id), []
            )
            with self.assertRaises(HTTPException) as raised:
                list_portal_preview_appointments(session, 999999)
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
