"""Rescheduling guards for fictional patient appointments."""

import unittest
from datetime import date, time

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.models import Appointment, AppointmentStatusChange, Base, Patient
from backend.scheduling import (
    record_appointment_status_change,
    reschedule_appointment,
)
from backend.schemas import AppointmentCreate


class AppointmentReschedulingTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Jamie",
                last_name="Example",
                date_of_birth=date(1991, 8, 9),
                sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            self.patient_id = patient.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def store(self, *, status="scheduled", at=time(9, 0)):
        with Session(self.engine) as session:
            appointment = Appointment(
                patient_id=self.patient_id,
                scheduled_date=date(2026, 11, 18),
                start_time=at,
                duration_minutes=30,
                reason_for_visit="Synthetic visit",
                status=status,
            )
            session.add(appointment)
            session.flush()
            appointment_id = appointment.id
            record_appointment_status_change(session, appointment, None)
            session.commit()
        return appointment_id

    def replacement(self, *, status="scheduled", at=time(10, 0)):
        return AppointmentCreate(
            scheduled_date=date(2026, 11, 19),
            start_time=at,
            duration_minutes=45,
            reason_for_visit="Rescheduled fictional visit",
            status=status,
        )

    def test_scheduled_visit_can_be_rescheduled_without_status_change(self):
        appointment_id = self.store()
        with Session(self.engine) as session:
            updated = reschedule_appointment(
                session, appointment_id, self.replacement()
            )
            self.assertEqual(updated.status, "scheduled")
            session.commit()

        with Session(self.engine) as session:
            stored = session.get(Appointment, appointment_id)
            self.assertEqual(stored.scheduled_date, date(2026, 11, 19))
            self.assertEqual(stored.start_time, time(10, 0))
            self.assertEqual(stored.duration_minutes, 45)
            self.assertEqual(stored.reason_for_visit, "Rescheduled fictional visit")
            events = session.scalars(
                select(AppointmentStatusChange).where(
                    AppointmentStatusChange.appointment_id == appointment_id
                )
            ).all()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].new_status, "scheduled")

    def test_checked_in_and_finalized_visits_cannot_be_edited(self):
        for status in ("checked_in", "completed", "cancelled", "no_show"):
            with self.subTest(status=status):
                appointment_id = self.store(status=status)
                with Session(self.engine) as session:
                    with self.assertRaises(HTTPException) as raised:
                        reschedule_appointment(
                            session, appointment_id, self.replacement(status=status)
                        )
                    self.assertEqual(raised.exception.status_code, 409)
                    session.rollback()
                with Session(self.engine) as session:
                    stored = session.get(Appointment, appointment_id)
                    self.assertEqual(stored.start_time, time(9, 0))
                    self.assertEqual(stored.status, status)

    def test_status_cannot_change_through_edit(self):
        appointment_id = self.store()
        for requested in ("checked_in", "completed", "cancelled", "no_show"):
            with self.subTest(requested=requested):
                with Session(self.engine) as session:
                    with self.assertRaises(HTTPException) as raised:
                        reschedule_appointment(
                            session, appointment_id,
                            self.replacement(status=requested),
                        )
                    self.assertEqual(raised.exception.status_code, 409)
                    session.rollback()
        with Session(self.engine) as session:
            stored = session.get(Appointment, appointment_id)
            self.assertEqual(stored.status, "scheduled")
            self.assertEqual(stored.start_time, time(9, 0))

    def test_reschedule_into_existing_slot_is_rejected(self):
        self.store(at=time(10, 0))
        moving_id = self.store(at=time(11, 0))
        with Session(self.engine) as session:
            conflicting = AppointmentCreate(
                scheduled_date=date(2026, 11, 18),
                start_time=time(10, 15),
                duration_minutes=30,
                reason_for_visit="Synthetic visit",
                status="scheduled",
            )
            with self.assertRaises(HTTPException) as raised:
                reschedule_appointment(session, moving_id, conflicting)
            self.assertEqual(raised.exception.status_code, 409)
            session.rollback()
        with Session(self.engine) as session:
            self.assertEqual(
                session.get(Appointment, moving_id).start_time, time(11, 0)
            )

    def test_same_slot_can_be_edited_without_self_conflict(self):
        appointment_id = self.store()
        with Session(self.engine) as session:
            updated = reschedule_appointment(
                session,
                appointment_id,
                AppointmentCreate(
                    scheduled_date=date(2026, 11, 18),
                    start_time=time(9, 0),
                    duration_minutes=30,
                    reason_for_visit="Updated fictional reason",
                    status="scheduled",
                ),
            )
            session.commit()
            self.assertEqual(updated.reason_for_visit, "Updated fictional reason")

    def test_missing_appointment_returns_not_found(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                reschedule_appointment(session, 999, self.replacement())
            self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
