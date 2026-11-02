"""Draft visit notes can link to their own patient's chart problems."""

import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.encounter_problems import (
    link_encounter_problem,
    list_encounter_problems,
    unlink_encounter_problem,
)
from backend.models import Base, Encounter, EncounterProblem, Patient, Problem
from backend.schemas import EncounterProblemLinkCreate, EncounterProblemRead


class EncounterProblemTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="River", last_name="Example",
                date_of_birth=date(1987, 6, 12), sex_at_birth="unknown",
            )
            other = Patient(
                first_name="Morgan", last_name="Sample",
                date_of_birth=date(1986, 2, 17), sex_at_birth="unknown",
            )
            session.add_all([patient, other])
            session.flush()
            self.patient_id, self.other_patient_id = patient.id, other.id
            problem = Problem(patient_id=patient.id, name="Synthetic asthma", status="active")
            other_problem = Problem(patient_id=other.id, name="Fictional sprain", status="active")
            note = Encounter(
                patient_id=patient.id, visit_date=date(2026, 10, 20),
                reason_for_visit="Synthetic checkup", assessment="Fictional review",
            )
            session.add_all([problem, other_problem, note])
            session.flush()
            self.problem_id, self.other_problem_id, self.encounter_id = (
                problem.id, other_problem.id, note.id
            )
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def link(self, session, problem_id=None):
        return link_encounter_problem(
            session, self.encounter_id,
            EncounterProblemLinkCreate(problem_id=problem_id or self.problem_id),
        )

    def test_link_records_snapshot_without_changing_chart_problem(self):
        with Session(self.engine) as session:
            link = self.link(session)
            session.commit()
            session.refresh(link)
            record = EncounterProblemRead.model_validate(link)
            self.assertEqual(record.problem_name_at_link, "Synthetic asthma")
            self.assertEqual(record.problem_status_at_link, "active")
            self.assertIsNotNone(record.linked_at)
            self.assertEqual(record.encounter_id, self.encounter_id)

        with Session(self.engine) as session:
            problem = session.get(Problem, self.problem_id)
            problem.name = "Renamed fictional condition"
            problem.status = "resolved"
            session.commit()

        with Session(self.engine) as session:
            record = list_encounter_problems(session, self.encounter_id)[0]
            self.assertEqual(record.problem_name_at_link, "Synthetic asthma")
            self.assertEqual(record.problem_status_at_link, "active")
            self.assertEqual(session.get(Problem, self.problem_id).name, "Renamed fictional condition")

    def test_duplicate_link_returns_conflict(self):
        with Session(self.engine) as session:
            self.link(session)
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session)
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(len(list_encounter_problems(session, self.encounter_id)), 1)

    def test_database_enforces_unique_pair(self):
        with Session(self.engine) as session:
            for _ in range(2):
                session.add(EncounterProblem(
                    encounter_id=self.encounter_id, problem_id=self.problem_id,
                    problem_name_at_link="Synthetic asthma", problem_status_at_link="active",
                ))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_other_patients_problem_is_not_accessible(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session, self.other_problem_id)
            self.assertEqual(raised.exception.status_code, 404)
            self.assertEqual(list_encounter_problems(session, self.encounter_id), [])

    def test_missing_problem_or_encounter_returns_not_found(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session, 9999)
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                link_encounter_problem(
                    session, 9999, EncounterProblemLinkCreate(problem_id=self.problem_id)
                )
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                list_encounter_problems(session, 9999)
            self.assertEqual(raised.exception.status_code, 404)

    def test_draft_link_can_be_removed_and_relinked(self):
        with Session(self.engine) as session:
            self.link(session)
            session.commit()
        with Session(self.engine) as session:
            unlink_encounter_problem(session, self.encounter_id, self.problem_id)
            session.commit()
            self.assertEqual(list_encounter_problems(session, self.encounter_id), [])
            self.link(session)
            session.commit()
            self.assertEqual(len(list_encounter_problems(session, self.encounter_id)), 1)

    def test_missing_link_cannot_be_removed(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                unlink_encounter_problem(session, self.encounter_id, self.problem_id)
            self.assertEqual(raised.exception.status_code, 404)

    def test_finalized_note_cannot_add_or_remove_problem_links(self):
        with Session(self.engine) as session:
            self.link(session)
            session.get(Encounter, self.encounter_id).finalized_at = datetime.now(timezone.utc)
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session)
            self.assertEqual(raised.exception.status_code, 409)
            with self.assertRaises(HTTPException) as raised:
                unlink_encounter_problem(session, self.encounter_id, self.problem_id)
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(len(list_encounter_problems(session, self.encounter_id)), 1)

    def test_link_input_is_strict(self):
        for invalid in (0, -1):
            with self.assertRaises(ValidationError):
                EncounterProblemLinkCreate(problem_id=invalid)
        with self.assertRaises(ValidationError):
            EncounterProblemLinkCreate.model_validate({"problem_id": self.problem_id, "encounter_id": 20})


if __name__ == "__main__":
    unittest.main()
