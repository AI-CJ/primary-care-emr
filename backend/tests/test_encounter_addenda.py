"""A finalized synthetic visit note can receive new addenda, not edits."""

import unittest
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.encounters import (
    apply_encounter_update,
    create_encounter,
    create_encounter_addendum,
    finalize_encounter,
)
from backend.models import Base, Encounter, EncounterAddendum, Patient
from backend.schemas import (
    EncounterAddendumCreate,
    EncounterAddendumRead,
    EncounterCreate,
    EncounterUpdate,
)


VISIT_DATE = date(2026, 10, 20)


class EncounterAddendumTests(unittest.TestCase):
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

    def make_note(self, *, finalize=True):
        with Session(self.engine) as session:
            note = create_encounter(
                session,
                self.patient_id,
                EncounterCreate(
                    visit_date=VISIT_DATE,
                    reason_for_visit="Synthetic checkup",
                    assessment="Fictional assessment",
                    plan="Synthetic plan",
                ),
            )
            session.flush()
            encounter_id = note.id
            if finalize:
                finalize_encounter(session, encounter_id)
            session.commit()
            return encounter_id

    def test_addendum_is_stored_separately_from_finalized_note(self):
        encounter_id = self.make_note()
        with Session(self.engine) as session:
            added = create_encounter_addendum(
                session, encounter_id,
                EncounterAddendumCreate(content="  Follow-up clarification.  "),
            )
            session.commit()
            session.refresh(added)
            record = EncounterAddendumRead.model_validate(added)
            self.assertEqual(record.content, "Follow-up clarification.")
            self.assertEqual(record.encounter_id, encounter_id)
            self.assertIsNotNone(record.created_at)

        with Session(self.engine) as session:
            note = session.get(Encounter, encounter_id)
            self.assertEqual(note.assessment, "Fictional assessment")
            self.assertEqual(note.plan, "Synthetic plan")
            self.assertIsNotNone(note.finalized_at)
            self.assertEqual(len(session.scalars(select(EncounterAddendum)).all()), 1)
            with self.assertRaises(HTTPException) as raised:
                apply_encounter_update(
                    session, encounter_id,
                    EncounterUpdate(
                        visit_date=VISIT_DATE,
                        reason_for_visit="Rewrite",
                        assessment="Altered",
                        plan="Altered",
                    ),
                )
            self.assertEqual(raised.exception.status_code, 409)

    def test_multiple_addenda_are_separate_records(self):
        encounter_id = self.make_note()
        with Session(self.engine) as session:
            for content in ("First clarification", "Second clarification"):
                create_encounter_addendum(
                    session, encounter_id, EncounterAddendumCreate(content=content)
                )
            session.commit()
        with Session(self.engine) as session:
            records = list(session.scalars(
                select(EncounterAddendum)
                .where(EncounterAddendum.encounter_id == encounter_id)
                .order_by(EncounterAddendum.created_at, EncounterAddendum.id)
            ))
            self.assertEqual([entry.content for entry in records], [
                "First clarification", "Second clarification"
            ])
            self.assertNotEqual(records[0].id, records[1].id)

    def test_draft_cannot_have_addendum(self):
        encounter_id = self.make_note(finalize=False)
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_encounter_addendum(
                    session, encounter_id,
                    EncounterAddendumCreate(content="Not final yet"),
                )
            self.assertEqual(raised.exception.status_code, 409)
            session.rollback()
        with Session(self.engine) as session:
            self.assertEqual(len(session.scalars(select(EncounterAddendum)).all()), 0)

    def test_missing_encounter_returns_not_found(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_encounter_addendum(
                    session, 999, EncounterAddendumCreate(content="No parent")
                )
            self.assertEqual(raised.exception.status_code, 404)

    def test_addendum_rejects_blank_and_unexpected_fields(self):
        for invalid in ("", "   ", "x" * 4001):
            with self.subTest(invalid=invalid[:12]):
                with self.assertRaises(ValidationError):
                    EncounterAddendumCreate(content=invalid)
        with self.assertRaises(ValidationError):
            EncounterAddendumCreate.model_validate({
                "content": "Attempt", "created_at": "2026-10-01T12:00:00Z"
            })


if __name__ == "__main__":
    unittest.main()
