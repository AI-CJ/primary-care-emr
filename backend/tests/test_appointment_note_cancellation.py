"""Keep documented visits from being cancelled as appointments."""

import unittest
from datetime import date, datetime, time, timezone
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.main import read_patient_appointments
from backend.models import (
    Appointment, AppointmentStatusChange, Base, Encounter, Patient,
)
from backend.scheduling import cancel_appointment, record_appointment_status_change


VISIT_DATE = date(2026, 11, 10)


class AppointmentNoteCancellationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Taylor",
                last_name="Example",
                date_of_birth=date(1994, 3, 8),
                sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            self.patient_id = patient.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def make_appointment(self, status="checked_in"):
        with Session(self.engine) as session:
            appointment = Appointment(
                patient_id=self.patient_id,
                scheduled_date=VISIT_DATE,
                start_time=time(9),
                duration_minutes=30,
                reason_for_visit="Fictional follow-up",
                status=status,
            )
            session.add(appointment)
            session.flush()
            record_appointment_status_change(session, appointment, None)
            appointment_id = appointment.id
            session.commit()
        return appointment_id

    def add_note(self, appointment_id=None, finalized=False):
        with Session(self.engine) as session:
            note = Encounter(
                patient_id=self.patient_id,
                appointment_id=appointment_id,
                visit_date=VISIT_DATE,
                reason_for_visit="Fictional follow-up",
                assessment="Example assessment",
                plan="Example plan",
                finalized_at=(
                    datetime(2026, 11, 10, 15, tzinfo=timezone.utc)
                    if finalized else None
                ),
            )
            session.add(note)
            session.flush()
            note_id = note.id
            session.commit()
        return note_id

    def test_draft_and_finalized_notes_prevent_cancellation(self):
        for finalized in (False, True):
            with self.subTest(finalized=finalized):
                appointment_id = self.make_appointment()
                note_id = self.add_note(appointment_id, finalized=finalized)
                with Session(self.engine) as session:
                    with self.assertRaises(HTTPException) as raised:
                        cancel_appointment(session, appointment_id)
                    self.assertEqual(raised.exception.status_code, 409)
                    self.assertIn("linked visit note", raised.exception.detail)
                    session.rollback()

                with Session(self.engine) as session:
                    appointment = session.get(Appointment, appointment_id)
                    note = session.get(Encounter, note_id)
                    history = list(session.scalars(
                        select(AppointmentStatusChange).where(
                            AppointmentStatusChange.appointment_id == appointment_id
                        )
                    ))
                    self.assertEqual(appointment.status, "checked_in")
                    self.assertEqual(note.appointment_id, appointment_id)
                    self.assertEqual(len(history), 1)
                    self.assertEqual(history[0].new_status, "checked_in")

    def test_undocumented_visits_can_still_be_cancelled(self):
        for initial_status in ("scheduled", "checked_in"):
            with self.subTest(initial_status=initial_status):
                appointment_id = self.make_appointment(initial_status)
                with Session(self.engine) as session:
                    cancel_appointment(session, appointment_id)
                    session.commit()

                with Session(self.engine) as session:
                    appointment = session.get(Appointment, appointment_id)
                    history = list(session.scalars(
                        select(AppointmentStatusChange)
                        .where(AppointmentStatusChange.appointment_id == appointment_id)
                        .order_by(AppointmentStatusChange.id)
                    ))
                    self.assertEqual(appointment.status, "cancelled")
                    self.assertEqual(len(history), 2)
                    self.assertEqual(
                        (history[-1].previous_status, history[-1].new_status),
                        (initial_status, "cancelled"),
                    )

    def test_standalone_note_does_not_block_cancellation(self):
        appointment_id = self.make_appointment()
        note_id = self.add_note()
        with Session(self.engine) as session:
            cancel_appointment(session, appointment_id)
            session.commit()
        with Session(self.engine) as session:
            self.assertEqual(
                session.get(Appointment, appointment_id).status, "cancelled"
            )
            self.assertIsNone(session.get(Encounter, note_id).appointment_id)


    def test_patient_appointments_show_linked_notes_without_clinical_text(self):
        draft_appointment = self.make_appointment()
        finalized_appointment = self.make_appointment(status="completed")
        unlinked_appointment = self.make_appointment(status="scheduled")
        draft_id = self.add_note(draft_appointment)
        finalized_id = self.add_note(finalized_appointment, finalized=True)
        self.add_note()  # A standalone note is not tied to an appointment.

        with patch("backend.main.engine", self.engine):
            records = read_patient_appointments(self.patient_id)

        by_id = {record.id: record for record in records}
        self.assertEqual(len(by_id), 3)
        self.assertEqual(by_id[draft_appointment].visit_note_id, draft_id)
        self.assertEqual(by_id[finalized_appointment].visit_note_id, finalized_id)
        self.assertIsNone(by_id[unlinked_appointment].visit_note_id)
        self.assertEqual(by_id[draft_appointment].status, "checked_in")
        self.assertNotIn("assessment", by_id[draft_appointment].model_dump())
        self.assertNotIn("plan", by_id[draft_appointment].model_dump())

    def test_appointment_list_does_not_include_other_patients(self):
        with Session(self.engine) as session:
            other_patient = Patient(
                first_name="Morgan",
                last_name="Example",
                date_of_birth=date(1987, 4, 9),
                sex_at_birth="unknown",
            )
            session.add(other_patient)
            session.flush()
            other_appointment = Appointment(
                patient_id=other_patient.id,
                scheduled_date=VISIT_DATE,
                start_time=time(10),
                duration_minutes=30,
                reason_for_visit="Other fictional visit",
                status="checked_in",
            )
            session.add(other_appointment)
            session.flush()
            session.add(Encounter(
                patient_id=other_patient.id,
                appointment_id=other_appointment.id,
                visit_date=VISIT_DATE,
                reason_for_visit="Other fictional visit",
            ))
            session.commit()

        own_appointment = self.make_appointment()
        with patch("backend.main.engine", self.engine):
            records = read_patient_appointments(self.patient_id)
        self.assertEqual([record.id for record in records], [own_appointment])
        self.assertIsNone(records[0].visit_note_id)

    def test_appointment_list_rejects_unknown_patient(self):
        with patch("backend.main.engine", self.engine):
            with self.assertRaises(HTTPException) as raised:
                read_patient_appointments(987654)
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
