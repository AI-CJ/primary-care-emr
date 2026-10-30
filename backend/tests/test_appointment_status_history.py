"""Appointment status-history tests using fictional records only."""

import unittest
from datetime import date, time

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.models import Appointment, AppointmentStatusChange, Base, Patient
from backend.scheduling import (
    cancel_appointment,
    check_in_appointment,
    complete_appointment,
    record_appointment_status_change,
)


class AppointmentStatusHistoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Jordan",
                last_name="Example",
                date_of_birth=date(1992, 4, 3),
                sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            self.patient_id = patient.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def create_appointment(self, record_creation=True):
        with Session(self.engine) as session:
            appointment = Appointment(
                patient_id=self.patient_id,
                scheduled_date=date(2026, 11, 14),
                start_time=time(10, 30),
                duration_minutes=30,
                reason_for_visit="Synthetic check-up",
                status="scheduled",
            )
            session.add(appointment)
            session.flush()
            appointment_id = appointment.id
            if record_creation:
                record_appointment_status_change(session, appointment, None)
            session.commit()
        return appointment_id

    def events(self, appointment_id):
        with Session(self.engine) as session:
            return list(session.scalars(
                select(AppointmentStatusChange)
                .where(AppointmentStatusChange.appointment_id == appointment_id)
                .order_by(
                    AppointmentStatusChange.changed_at,
                    AppointmentStatusChange.id,
                )
            ).all())

    def test_initial_status_and_timestamp_are_recorded(self):
        appointment_id = self.create_appointment()
        records = self.events(appointment_id)
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0].previous_status)
        self.assertEqual(records[0].new_status, "scheduled")
        self.assertIsNotNone(records[0].changed_at)

    def test_check_in_and_completion_append_ordered_transitions(self):
        appointment_id = self.create_appointment()
        with Session(self.engine) as session:
            check_in_appointment(session, appointment_id)
            session.commit()
        with Session(self.engine) as session:
            complete_appointment(session, appointment_id)
            session.commit()

        records = self.events(appointment_id)
        self.assertEqual(
            [(event.previous_status, event.new_status) for event in records],
            [(None, "scheduled"), ("scheduled", "checked_in"),
             ("checked_in", "completed")],
        )

    def test_cancellation_records_change_but_noop_edit_does_not(self):
        appointment_id = self.create_appointment()
        with Session(self.engine) as session:
            appointment = session.get(Appointment, appointment_id)
            record_appointment_status_change(session, appointment, "scheduled")
            appointment.status = "cancelled"
            record_appointment_status_change(session, appointment, "scheduled")
            session.commit()
        records = self.events(appointment_id)
        self.assertEqual(len(records), 2)
        self.assertEqual(
            (records[-1].previous_status, records[-1].new_status),
            ("scheduled", "cancelled"),
        )

    def test_invalid_transition_does_not_add_an_event(self):
        appointment_id = self.create_appointment()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                complete_appointment(session, appointment_id)
            self.assertEqual(raised.exception.status_code, 409)
            session.rollback()
        self.assertEqual(len(self.events(appointment_id)), 1)

    def test_transaction_rollback_discards_status_and_history(self):
        appointment_id = self.create_appointment()
        with Session(self.engine) as session:
            check_in_appointment(session, appointment_id)
            session.rollback()
        self.assertEqual(len(self.events(appointment_id)), 1)
        with Session(self.engine) as session:
            appointment = session.get(Appointment, appointment_id)
            self.assertEqual(appointment.status, "scheduled")

    def test_older_appointments_have_no_fabricated_history(self):
        appointment_id = self.create_appointment(record_creation=False)
        self.assertEqual(self.events(appointment_id), [])


    def test_cancellation_action_appends_status_history(self):
        for initial_status in ("scheduled", "checked_in"):
            with self.subTest(initial_status=initial_status):
                appointment_id = self.create_appointment()
                if initial_status == "checked_in":
                    with Session(self.engine) as session:
                        check_in_appointment(session, appointment_id)
                        session.commit()

                with Session(self.engine) as session:
                    cancel_appointment(session, appointment_id)
                    session.commit()

                records = self.events(appointment_id)
                self.assertEqual(
                    (records[-1].previous_status, records[-1].new_status),
                    (initial_status, "cancelled"),
                )
                self.assertEqual(
                    len(records),
                    2 if initial_status == "scheduled" else 3,
                )

                with Session(self.engine) as session:
                    with self.assertRaises(HTTPException) as raised:
                        cancel_appointment(session, appointment_id)
                    self.assertEqual(raised.exception.status_code, 409)
                self.assertEqual(len(self.events(appointment_id)), len(records))

    def test_cancellation_rollback_restores_status_and_history(self):
        appointment_id = self.create_appointment()
        with Session(self.engine) as session:
            cancel_appointment(session, appointment_id)
            session.rollback()

        with Session(self.engine) as session:
            self.assertEqual(
                session.get(Appointment, appointment_id).status, "scheduled"
            )
        self.assertEqual(len(self.events(appointment_id)), 1)


if __name__ == "__main__":
    unittest.main()
