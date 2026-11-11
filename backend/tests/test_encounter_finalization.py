"""Finalizing fictional visit notes makes their content read-only."""

import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.encounters import (
    apply_encounter_update,
    create_encounter,
    finalize_encounter,
)
from backend.models import Base, Encounter, Patient
from backend.schemas import EncounterCreate, EncounterRead, EncounterUpdate


VISIT_DATE = date(2026, 10, 20)


class EncounterFinalizationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="River",
                last_name="Example",
                date_of_birth=date(1987, 6, 12),
                sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            self.patient_id = patient.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def make_note(self, *, assessment="Fictional assessment", plan="Synthetic plan"):
        with Session(self.engine) as session:
            encounter = create_encounter(
                session,
                self.patient_id,
                EncounterCreate(
                    visit_date=VISIT_DATE,
                    reason_for_visit="Synthetic checkup",
                    subjective="Fictional history",
                    assessment=assessment,
                    plan=plan,
                ),
            )
            session.flush()
            encounter_id = encounter.id
            session.commit()
        return encounter_id

    def test_finalized_timestamp_is_returned_in_read_schema(self):
        encounter_id = self.make_note()
        with Session(self.engine) as session:
            note = finalize_encounter(session, encounter_id)
            session.commit()
            session.refresh(note)
            record = EncounterRead.model_validate(note)
            self.assertIsNotNone(record.finalized_at)

    def test_finalized_note_cannot_be_edited_even_with_same_date(self):
        encounter_id = self.make_note()
        with Session(self.engine) as session:
            finalize_encounter(session, encounter_id)
            session.commit()

        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                apply_encounter_update(
                    session,
                    encounter_id,
                    EncounterUpdate(
                        visit_date=VISIT_DATE,
                        reason_for_visit="Changed reason",
                        assessment="Replaced assessment",
                        plan="Changed plan",
                    ),
                )
            self.assertEqual(raised.exception.status_code, 409)
            session.rollback()

        with Session(self.engine) as session:
            note = session.get(Encounter, encounter_id)
            self.assertEqual(note.reason_for_visit, "Synthetic checkup")
            self.assertEqual(note.assessment, "Fictional assessment")

    def test_draft_note_remains_editable(self):
        encounter_id = self.make_note()
        with Session(self.engine) as session:
            updated = apply_encounter_update(
                session,
                encounter_id,
                EncounterUpdate(
                    visit_date=VISIT_DATE,
                    reason_for_visit="Updated follow-up",
                    assessment="Updated fictional assessment",
                    plan="Synthetic plan",
                ),
            )
            session.commit()
            self.assertIsNone(updated.finalized_at)
            self.assertEqual(updated.reason_for_visit, "Updated follow-up")

    def test_patient_instructions_are_trimmed_and_frozen_on_finalization(self):
        with Session(self.engine) as session:
            note = create_encounter(
                session, self.patient_id,
                EncounterCreate(
                    visit_date=VISIT_DATE,
                    reason_for_visit="Fictional follow-up",
                    assessment="Synthetic assessment",
                    plan="Synthetic plan",
                    patient_instructions="  Keep a fictional reading log.  ",
                ),
            )
            session.flush()
            encounter_id = note.id
            session.commit()

        with Session(self.engine) as session:
            finalize_encounter(session, encounter_id)
            session.commit()
            with self.assertRaises(HTTPException) as raised:
                apply_encounter_update(
                    session, encounter_id,
                    EncounterUpdate(
                        visit_date=VISIT_DATE,
                        reason_for_visit="Fictional follow-up",
                        assessment="Synthetic assessment",
                        plan="Synthetic plan",
                        patient_instructions="Replace original instructions",
                    ),
                )
            self.assertEqual(raised.exception.status_code, 409)
            session.rollback()

        with Session(self.engine) as session:
            note = session.get(Encounter, encounter_id)
            self.assertEqual(note.patient_instructions, "Keep a fictional reading log.")

    def test_assessment_and_plan_required_for_finalization(self):
        for field in ("assessment", "plan"):
            with self.subTest(missing=field):
                kwargs = {field: None}
                encounter_id = self.make_note(**kwargs)
                with Session(self.engine) as session:
                    with self.assertRaises(HTTPException) as raised:
                        finalize_encounter(session, encounter_id)
                    self.assertEqual(raised.exception.status_code, 409)
                    session.rollback()
                with Session(self.engine) as session:
                    self.assertIsNone(
                        session.get(Encounter, encounter_id).finalized_at
                    )

    def test_finalization_cannot_be_repeated(self):
        encounter_id = self.make_note()
        with Session(self.engine) as session:
            finalize_encounter(session, encounter_id)
            session.commit()

        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                finalize_encounter(session, encounter_id)
            self.assertEqual(raised.exception.status_code, 409)

    def test_missing_note_returns_not_found(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                finalize_encounter(session, 999)
            self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
