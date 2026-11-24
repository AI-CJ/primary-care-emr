"""Archived charts preserve appointment requests but reject active queue work."""

import unittest
from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.appointment_change_requests import (
    AppointmentChangeRequestCreate,
    list_patient_change_requests,
    list_pending_change_requests,
    review_change_request,
    submit_appointment_change_request,
)
from backend.models import Appointment, Base, Patient


class ArchivedAppointmentChangeRequestTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        future = date.today() + timedelta(days=14)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Archive", last_name="Request",
                date_of_birth=date(1991, 5, 6), sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            appointments = [
                Appointment(
                    patient_id=patient.id, scheduled_date=future,
                    start_time=time(10), duration_minutes=30,
                    reason_for_visit="Synthetic request one", status="scheduled",
                ),
                Appointment(
                    patient_id=patient.id, scheduled_date=future,
                    start_time=time(11), duration_minutes=30,
                    reason_for_visit="Synthetic request two", status="scheduled",
                ),
            ]
            session.add_all(appointments)
            session.commit()
            self.patient_id = patient.id
            self.appointment_ids = [row.id for row in appointments]

        with Session(self.engine) as session:
            record = submit_appointment_change_request(
                session, self.patient_id,
                AppointmentChangeRequestCreate(
                    appointment_id=self.appointment_ids[0], kind="reschedule",
                ),
            )
            self.request_id = record.id

    def tearDown(self):
        self.engine.dispose()

    def test_archive_blocks_submission_and_review_and_hides_active_queue(self):
        with Session(self.engine) as session:
            session.get(Patient, self.patient_id).archived_at = datetime.now(timezone.utc)
            session.commit()

        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as submitted:
                submit_appointment_change_request(
                    session, self.patient_id,
                    AppointmentChangeRequestCreate(
                        appointment_id=self.appointment_ids[1], kind="cancel",
                    ),
                )
            self.assertEqual(submitted.exception.status_code, 409)
            self.assertIn("Archived", submitted.exception.detail)

        with Session(self.engine) as session:
            self.assertEqual(list_pending_change_requests(session), [])
            self.assertEqual(
                [row.id for row in list_patient_change_requests(session, self.patient_id)],
                [self.request_id],
            )
            with self.assertRaises(HTTPException) as reviewed:
                review_change_request(session, self.request_id)
            self.assertEqual(reviewed.exception.status_code, 409)
            self.assertIn("Archived", reviewed.exception.detail)

        with Session(self.engine) as session:
            session.get(Patient, self.patient_id).archived_at = None
            session.commit()

        with Session(self.engine) as session:
            self.assertEqual(
                [row.id for row in list_pending_change_requests(session)],
                [self.request_id],
            )
            reviewed = review_change_request(session, self.request_id)
            self.assertEqual(reviewed.status, "reviewed")

        with Session(self.engine) as session:
            new_request = submit_appointment_change_request(
                session, self.patient_id,
                AppointmentChangeRequestCreate(
                    appointment_id=self.appointment_ids[1], kind="cancel",
                ),
            )
            self.assertEqual(new_request.status, "pending")


if __name__ == "__main__":
    unittest.main()
