"""Appointment check-in and status transitions (synthetic data only)."""

import unittest
from datetime import date, time

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Appointment, Base, Patient
from backend.scheduling import (
    cancel_appointment,
    check_in_appointment,
    complete_appointment,
    ensure_appointment_status_transition,
    mark_appointment_no_show,
)


class AppointmentLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Taylor",
                last_name="Sample",
                date_of_birth=date(1990, 5, 10),
                sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            self.patient_id = patient.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def store_appointment(self, status="scheduled"):
        with Session(self.engine) as session:
            appointment = Appointment(
                patient_id=self.patient_id,
                scheduled_date=date(2026, 11, 12),
                start_time=time(9, 0),
                duration_minutes=30,
                reason_for_visit="Synthetic office visit",
                status=status,
            )
            session.add(appointment)
            session.flush()
            appointment_id = appointment.id
            session.commit()
        return appointment_id

    def test_allowed_transitions(self):
        cases = (
            ("scheduled", "scheduled"),
            ("scheduled", "checked_in"),
            ("scheduled", "cancelled"),
            ("scheduled", "no_show"),
            ("checked_in", "checked_in"),
            ("checked_in", "completed"),
            ("checked_in", "cancelled"),
            ("completed", "completed"),
            ("cancelled", "cancelled"),
            ("no_show", "no_show"),
        )
        for current, requested in cases:
            with self.subTest(current=current, requested=requested):
                ensure_appointment_status_transition(current, requested)

    def test_invalid_transitions_return_conflict(self):
        cases = (
            ("scheduled", "completed"),
            ("checked_in", "scheduled"),
            ("completed", "scheduled"),
            ("completed", "cancelled"),
            ("cancelled", "checked_in"),
            ("cancelled", "scheduled"),
            ("checked_in", "no_show"),
            ("completed", "no_show"),
            ("cancelled", "no_show"),
            ("no_show", "scheduled"),
            ("no_show", "checked_in"),
            ("no_show", "cancelled"),
        )
        for current, requested in cases:
            with self.subTest(current=current, requested=requested):
                with self.assertRaises(HTTPException) as raised:
                    ensure_appointment_status_transition(current, requested)
                self.assertEqual(raised.exception.status_code, 409)

    def test_scheduled_visit_can_be_checked_in_once(self):
        appointment_id = self.store_appointment()
        with Session(self.engine) as session:
            appointment = check_in_appointment(session, appointment_id)
            self.assertEqual(appointment.status, "checked_in")
            session.commit()

        with Session(self.engine) as session:
            self.assertEqual(
                session.get(Appointment, appointment_id).status,
                "checked_in",
            )
            with self.assertRaises(HTTPException) as raised:
                check_in_appointment(session, appointment_id)
            self.assertEqual(raised.exception.status_code, 409)

    def test_cancelled_and_completed_visits_cannot_check_in(self):
        for status in ("cancelled", "completed", "checked_in"):
            with self.subTest(status=status):
                appointment_id = self.store_appointment(status)
                with Session(self.engine) as session:
                    with self.assertRaises(HTTPException) as raised:
                        check_in_appointment(session, appointment_id)
                    self.assertEqual(raised.exception.status_code, 409)
                    self.assertEqual(
                        session.get(Appointment, appointment_id).status,
                        status,
                    )

    def test_missing_appointment_returns_not_found(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                check_in_appointment(session, 999)
            self.assertEqual(raised.exception.status_code, 404)


    def test_checked_in_visit_can_be_completed_once(self):
        appointment_id = self.store_appointment(status="checked_in")
        with Session(self.engine) as session:
            appointment = complete_appointment(session, appointment_id)
            self.assertEqual(appointment.status, "completed")
            session.commit()

        with Session(self.engine) as session:
            self.assertEqual(
                session.get(Appointment, appointment_id).status,
                "completed",
            )
            with self.assertRaises(HTTPException) as raised:
                complete_appointment(session, appointment_id)
            self.assertEqual(raised.exception.status_code, 409)

    def test_completion_rejects_appointments_not_checked_in(self):
        for status in ("scheduled", "cancelled", "completed"):
            with self.subTest(status=status):
                appointment_id = self.store_appointment(status)
                with Session(self.engine) as session:
                    with self.assertRaises(HTTPException) as raised:
                        complete_appointment(session, appointment_id)
                    self.assertEqual(raised.exception.status_code, 409)
                    self.assertEqual(
                        session.get(Appointment, appointment_id).status,
                        status,
                    )

    def test_check_in_then_complete(self):
        appointment_id = self.store_appointment()
        with Session(self.engine) as session:
            check_in_appointment(session, appointment_id)
            session.commit()
        with Session(self.engine) as session:
            complete_appointment(session, appointment_id)
            session.commit()
        with Session(self.engine) as session:
            self.assertEqual(
                session.get(Appointment, appointment_id).status, "completed"
            )

    def test_completion_of_missing_appointment_returns_not_found(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                complete_appointment(session, 999)
            self.assertEqual(raised.exception.status_code, 404)


    def test_cancellation_from_scheduled_or_checked_in(self):
        for status in ("scheduled", "checked_in"):
            with self.subTest(status=status):
                appointment_id = self.store_appointment(status=status)
                with Session(self.engine) as session:
                    appointment = cancel_appointment(session, appointment_id)
                    self.assertEqual(appointment.status, "cancelled")
                    session.commit()
                with Session(self.engine) as session:
                    self.assertEqual(
                        session.get(Appointment, appointment_id).status,
                        "cancelled",
                    )
                    with self.assertRaises(HTTPException) as raised:
                        cancel_appointment(session, appointment_id)
                    self.assertEqual(raised.exception.status_code, 409)

    def test_cancellation_rejects_finished_visits(self):
        for status in ("completed", "cancelled"):
            with self.subTest(status=status):
                appointment_id = self.store_appointment(status=status)
                with Session(self.engine) as session:
                    with self.assertRaises(HTTPException) as raised:
                        cancel_appointment(session, appointment_id)
                    self.assertEqual(raised.exception.status_code, 409)
                    self.assertEqual(
                        session.get(Appointment, appointment_id).status,
                        status,
                    )

    def test_cancellation_of_missing_appointment_returns_not_found(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                cancel_appointment(session, 999)
            self.assertEqual(raised.exception.status_code, 404)


    def test_scheduled_appointment_can_be_marked_no_show_once(self):
        appointment_id = self.store_appointment()
        with Session(self.engine) as session:
            appointment = mark_appointment_no_show(session, appointment_id)
            self.assertEqual(appointment.status, "no_show")
            session.commit()

        with Session(self.engine) as session:
            self.assertEqual(
                session.get(Appointment, appointment_id).status, "no_show"
            )
            with self.assertRaises(HTTPException) as raised:
                mark_appointment_no_show(session, appointment_id)
            self.assertEqual(raised.exception.status_code, 409)

    def test_no_show_rejects_any_non_scheduled_appointment(self):
        for status in ("checked_in", "completed", "cancelled", "no_show"):
            with self.subTest(status=status):
                appointment_id = self.store_appointment(status=status)
                with Session(self.engine) as session:
                    with self.assertRaises(HTTPException) as raised:
                        mark_appointment_no_show(session, appointment_id)
                    self.assertEqual(raised.exception.status_code, 409)
                    self.assertEqual(
                        session.get(Appointment, appointment_id).status,
                        status,
                    )

    def test_no_show_of_missing_appointment_returns_not_found(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                mark_appointment_no_show(session, 999)
            self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
