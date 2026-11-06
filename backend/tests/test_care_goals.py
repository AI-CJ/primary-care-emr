"""Care goals persist independently of individual visit notes."""

import unittest
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.care_goals import complete_care_goal, create_care_goal, list_care_goals
from backend.models import Base, CareGoal, Patient
from backend.schemas import CareGoalComplete, CareGoalCreate, CareGoalRead


class CareGoalTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            first = Patient(
                first_name="Avery", last_name="Example",
                date_of_birth=date(1988, 2, 14), sex_at_birth="unknown",
            )
            second = Patient(
                first_name="Morgan", last_name="Sample",
                date_of_birth=date(1991, 6, 21), sex_at_birth="unknown",
            )
            session.add_all([first, second])
            session.flush()
            self.first_id, self.second_id = first.id, second.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_create_and_list_goals_for_one_patient(self):
        with Session(self.engine) as session:
            older = create_care_goal(
                session, self.first_id,
                CareGoalCreate(title="  Walk after lunch  ", target_date=date(2027, 1, 15)),
            )
            newer = create_care_goal(
                session, self.first_id, CareGoalCreate(title="Track daily activity"),
            )
            other = create_care_goal(
                session, self.second_id, CareGoalCreate(title="Different patient's goal"),
            )
            session.commit()
            ids = (older.id, newer.id, other.id)

        with Session(self.engine) as session:
            listed = list_care_goals(session, self.first_id)
            self.assertEqual([goal.id for goal in listed], [ids[1], ids[0]])
            saved = CareGoalRead.model_validate(listed[1])
            self.assertEqual(saved.title, "Walk after lunch")
            self.assertEqual(saved.status, "active")
            self.assertEqual(saved.target_date, date(2027, 1, 15))
            self.assertIsNone(saved.completed_at)
            self.assertEqual([g.id for g in list_care_goals(session, self.second_id)], [ids[2]])

    def test_complete_goal_preserves_original_and_history(self):
        with Session(self.engine) as session:
            goal = create_care_goal(
                session, self.first_id, CareGoalCreate(title="Follow daily walking plan"),
            )
            session.commit()
            goal_id = goal.id

        with Session(self.engine) as session:
            completed = complete_care_goal(
                session, goal_id, CareGoalComplete(completion_note="  Met walking target. "),
            )
            result = CareGoalRead.model_validate(completed)
            session.commit()
            self.assertEqual(result.status, "completed")
            self.assertEqual(result.completion_note, "Met walking target.")
            self.assertIsNotNone(result.completed_at)
            self.assertEqual(result.title, "Follow daily walking plan")

        with Session(self.engine) as session:
            saved = list_care_goals(session, self.first_id)[0]
            self.assertEqual(saved.status, "completed")
            self.assertEqual(saved.title, "Follow daily walking plan")
            self.assertIsNotNone(saved.completed_at)

    def test_completion_cannot_overwrite_a_completed_goal(self):
        with Session(self.engine) as session:
            goal = create_care_goal(session, self.first_id, CareGoalCreate(title="Example"))
            session.commit()
            goal_id = goal.id

        with Session(self.engine) as session:
            complete_care_goal(session, goal_id, CareGoalComplete(completion_note="Original outcome"))
            session.commit()

        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                complete_care_goal(
                    session, goal_id, CareGoalComplete(completion_note="Replacement")
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(session.get(CareGoal, goal_id).completion_note, "Original outcome")

    def test_missing_patients_and_goals_return_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                list_care_goals(session, 99999)
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                create_care_goal(session, 99999, CareGoalCreate(title="Orphan"))
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                complete_care_goal(session, 99999, CareGoalComplete(completion_note="Missing"))
            self.assertEqual(raised.exception.status_code, 404)

    def test_validators_reject_blank_oversized_and_unrecognized_fields(self):
        for title in ("", "   ", "x" * 201):
            with self.assertRaises(ValidationError):
                CareGoalCreate(title=title)
        for note in ("", "  ", "x" * 2001):
            with self.assertRaises(ValidationError):
                CareGoalComplete(completion_note=note)
        with self.assertRaises(ValidationError):
            CareGoalCreate.model_validate({"title": "Test", "patient_id": self.first_id})
        with self.assertRaises(ValidationError):
            CareGoalComplete.model_validate({"completion_note": "Done", "status": "active"})


if __name__ == "__main__":
    unittest.main()
