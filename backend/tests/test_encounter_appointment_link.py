"""Appointment-linked visit notes with fictional patients only."""

import unittest
from datetime import date, time

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.encounters import create_encounter
from backend.models import Appointment, Base, Encounter, Patient
from backend.schemas import EncounterCreate, EncounterRead, EncounterUpdate


VISIT_DATE = date(2026, 10, 20)


class EncounterAppointmentLinkTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            first = Patient(
                first_name="Morgan",
                last_name="Sample",
                date_of_birth=date(1988, 4, 11),
                sex_at_birth="unknown",
            )
            second = Patient(
                first_name="Reese",
                last_name="Example",
                date_of_birth=date(1991, 2, 15),
                sex_at_birth="unknown",
            )
            session.add_all([first, second])
            session.flush()
            self.patient_id = first.id
            self.other_patient_id = second.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def appointment(self, status="checked_in"):
        with Session(self.engine) as session:
            appointment = Appointment(
                patient_id=self.patient_id,
                scheduled_date=VISIT_DATE,
                start_time=time(9),
                duration_minutes=30,
                reason_for_visit="Fictional checkup",
                status=status,
            )
            session.add(appointment)
            session.flush()
            appointment_id = appointment.id
            session.commit()
        return appointment_id

    def note(self, appointment_id=None, visit_date=VISIT_DATE):
        return EncounterCreate(
            appointment_id=appointment_id,
            visit_date=visit_date,
            reason_for_visit="Follow-up",
            assessment="Fictional assessment",
        )

    def test_checked_in_and_completed_appointments_accept_a_note(self):
        for status in ("checked_in", "completed"):
            with self.subTest(status=status):
                appointment_id = self.appointment(status)
                with Session(self.engine) as session:
                    encounter = create_encounter(
                        session, self.patient_id, self.note(appointment_id)
                    )
                    session.commit()
                    session.refresh(encounter)
                    record = EncounterRead.model_validate(encounter)
                    self.assertEqual(record.appointment_id, appointment_id)
                    self.assertEqual(record.patient_id, self.patient_id)
                    self.assertEqual(record.assessment, "Fictional assessment")

    def test_standalone_note_still_works(self):
        with Session(self.engine) as session:
            note = create_encounter(session, self.patient_id, self.note())
            session.commit()
            session.refresh(note)
            self.assertIsNone(note.appointment_id)

    def test_appointment_can_have_only_one_linked_note(self):
        appointment_id = self.appointment()
        with Session(self.engine) as session:
            create_encounter(session, self.patient_id, self.note(appointment_id))
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_encounter(
                    session, self.patient_id, self.note(appointment_id)
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(
                session.query(Encounter).filter_by(
                    appointment_id=appointment_id
                ).count(),
                1,
            )

    def test_database_enforces_unique_appointment_link(self):
        appointment_id = self.appointment()
        with Session(self.engine) as session:
            for _ in range(2):
                session.add(Encounter(
                    patient_id=self.patient_id,
                    appointment_id=appointment_id,
                    visit_date=VISIT_DATE,
                    reason_for_visit="Duplicate synthetic note",
                    assessment="Fictional assessment",
                ))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_cannot_link_an_appointment_from_another_patient(self):
        appointment_id = self.appointment()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_encounter(
                    session, self.other_patient_id, self.note(appointment_id)
                )
            self.assertEqual(raised.exception.status_code, 404)

    def test_missing_appointment_returns_not_found(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_encounter(session, self.patient_id, self.note(999))
            self.assertEqual(raised.exception.status_code, 404)

    def test_non_visit_appointment_cannot_be_linked(self):
        for status in ("scheduled", "cancelled", "no_show"):
            with self.subTest(status=status):
                appointment_id = self.appointment(status)
                with Session(self.engine) as session:
                    with self.assertRaises(HTTPException) as raised:
                        create_encounter(
                            session, self.patient_id, self.note(appointment_id)
                        )
                    self.assertEqual(raised.exception.status_code, 409)

    def test_linked_note_must_match_appointment_day(self):
        appointment_id = self.appointment()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_encounter(
                    session,
                    self.patient_id,
                    self.note(appointment_id, date(2026, 10, 21)),
                )
            self.assertEqual(raised.exception.status_code, 409)

    def test_missing_patient_returns_not_found(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_encounter(session, 999, self.note())
            self.assertEqual(raised.exception.status_code, 404)

    def test_note_update_cannot_change_appointment_link(self):
        fields = self.note().model_dump(exclude={"appointment_id"})
        with self.assertRaises(ValidationError):
            EncounterUpdate.model_validate({**fields, "appointment_id": 1})
        EncounterUpdate.model_validate(fields)


if __name__ == "__main__":
    unittest.main()
