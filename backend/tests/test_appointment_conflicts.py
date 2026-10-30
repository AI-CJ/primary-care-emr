"""Conflict checks for the synthetic patient appointment scheduler."""
import unittest
from datetime import date, time, timedelta, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Appointment, Base, Patient
from backend.scheduling import cancel_appointment, ensure_appointment_slot_open
from backend.schemas import AppointmentCreate


class AppointmentConflictTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.day = date(2026, 11, 12)

        with Session(self.engine) as session:
            patients = [
                Patient(
                    first_name="Taylor",
                    last_name="Sample",
                    date_of_birth=date(1990, 5, 10),
                    sex_at_birth="unknown",
                ),
                Patient(
                    first_name="Morgan",
                    last_name="Example",
                    date_of_birth=date(1988, 2, 3),
                    sex_at_birth="unknown",
                ),
            ]
            session.add_all(patients)
            session.flush()
            self.patient_a, self.patient_b = (patient.id for patient in patients)
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def appointment_data(
        self,
        *,
        start=time(9),
        duration=30,
        day=None,
        status="scheduled",
    ):
        return AppointmentCreate(
            scheduled_date=day or self.day,
            start_time=start,
            duration_minutes=duration,
            reason_for_visit="Synthetic office visit",
            status=status,
        )

    def store(self, *, patient_id=None, **overrides):
        data = self.appointment_data(**overrides)
        with Session(self.engine) as session:
            appointment = Appointment(
                patient_id=patient_id or self.patient_a,
                **data.model_dump(),
            )
            session.add(appointment)
            session.flush()
            appointment_id = appointment.id
            session.commit()
            return appointment_id

    def check(self, *, patient_id=None, exclude_id=None, **overrides):
        with Session(self.engine) as session:
            return ensure_appointment_slot_open(
                session,
                patient_id or self.patient_a,
                self.appointment_data(**overrides),
                exclude_appointment_id=exclude_id,
            )

    def test_overlap_is_rejected_with_conflict_status(self):
        self.store()
        with self.assertRaises(HTTPException) as raised:
            self.check(start=time(9, 15))
        self.assertEqual(raised.exception.status_code, 409)

    def test_touching_endpoints_are_not_overlapping(self):
        self.store()
        self.check(start=time(9, 30))
        self.check(start=time(8, 30))

    def test_different_patients_can_share_a_time(self):
        self.store()
        self.check(patient_id=self.patient_b)

    def test_cancelled_appointments_do_not_reserve_a_slot(self):
        self.store(status="cancelled")
        self.check()
        self.store(start=time(10))
        self.check(start=time(10), status="cancelled")

    def test_cancelling_appointment_releases_its_slot(self):
        appointment_id = self.store()
        with Session(self.engine) as session:
            cancel_appointment(session, appointment_id)
            session.commit()
        self.check()

    def test_completed_and_checked_in_appointments_reserve_a_slot(self):
        for status, start in (("completed", time(10)), ("checked_in", time(11))):
            with self.subTest(status=status):
                self.store(start=start, status=status)
                with self.assertRaises(HTTPException):
                    self.check(start=start)

    def test_updating_own_appointment_is_not_a_conflict(self):
        appointment_id = self.store()
        self.check(exclude_id=appointment_id)

    def test_edit_cannot_move_into_another_slot(self):
        self.store(start=time(9))
        moving_id = self.store(start=time(11))
        with self.assertRaises(HTTPException):
            self.check(start=time(9, 15), exclude_id=moving_id)

    def test_visits_overlapping_midnight_conflict(self):
        self.store(start=time(23, 45), duration=60)
        with self.assertRaises(HTTPException):
            self.check(start=time(0, 15), day=self.day + timedelta(days=1))
        self.check(start=time(0, 45), day=self.day + timedelta(days=1))

    def test_new_late_visit_cannot_overlap_next_day_booking(self):
        self.store(day=self.day + timedelta(days=1), start=time(0, 15))
        with self.assertRaises(HTTPException):
            self.check(start=time(23, 45), duration=60)

    def test_appointment_start_must_be_clinic_local(self):
        with self.assertRaises(ValidationError):
            self.appointment_data(start=time(9, tzinfo=timezone(timedelta(hours=-4))))


if __name__ == "__main__":
    unittest.main()
