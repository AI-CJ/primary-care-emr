"""Progress notes form a permanent timeline for an active care goal."""

import unittest
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.care_goals import (
    complete_care_goal,
    create_care_goal,
    list_goal_progress,
    record_goal_progress,
)
from backend.models import Base, CareGoal, Patient
from backend.schemas import (
    CareGoalComplete,
    CareGoalCreate,
    CareGoalProgressCreate,
    CareGoalProgressRead,
)


class CareGoalProgressTests(unittest.TestCase):
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
            self.first_goal = create_care_goal(
                session, first.id, CareGoalCreate(title="Practice a daily walk")
            ).id
            self.second_goal = create_care_goal(
                session, second.id, CareGoalCreate(title="Track nutrition")
            ).id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_progress_entries_are_chronological_and_separate_by_goal(self):
        with Session(self.engine) as session:
            first = record_goal_progress(
                session, self.first_goal,
                CareGoalProgressCreate(note="  Walked on Monday.  "),
            )
            second = record_goal_progress(
                session, self.first_goal,
                CareGoalProgressCreate(note="Walked on Wednesday."),
            )
            record_goal_progress(
                session, self.second_goal,
                CareGoalProgressCreate(note="Recorded meals."),
            )
            first_id, second_id = first.id, second.id
            session.commit()

        with Session(self.engine) as session:
            entries = list_goal_progress(session, self.first_goal)
            self.assertEqual([entry.id for entry in entries], [first_id, second_id])
            self.assertEqual(entries[0].note, "Walked on Monday.")
            self.assertEqual(entries[1].note, "Walked on Wednesday.")
            read = CareGoalProgressRead.model_validate(entries[0])
            self.assertEqual(read.goal_id, self.first_goal)
            self.assertIsNotNone(read.recorded_at)
            self.assertEqual(len(list_goal_progress(session, self.second_goal)), 1)

    def test_completed_goal_keeps_entries_but_rejects_new_progress(self):
        with Session(self.engine) as session:
            entry = record_goal_progress(
                session, self.first_goal, CareGoalProgressCreate(note="First update")
            )
            entry_id = entry.id
            complete_care_goal(
                session, self.first_goal,
                CareGoalComplete(completion_note="Goal achieved"),
            )
            session.commit()

        with Session(self.engine) as session:
            entries = list_goal_progress(session, self.first_goal)
            self.assertEqual([entry.id for entry in entries], [entry_id])
            with self.assertRaises(HTTPException) as raised:
                record_goal_progress(
                    session, self.first_goal,
                    CareGoalProgressCreate(note="Should not be added"),
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(len(list_goal_progress(session, self.first_goal)), 1)
            self.assertEqual(session.get(CareGoal, self.first_goal).status, "completed")

    def test_missing_goal_returns_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                list_goal_progress(session, 99999)
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                record_goal_progress(
                    session, 99999, CareGoalProgressCreate(note="Missing goal")
                )
            self.assertEqual(raised.exception.status_code, 404)

    def test_progress_note_validation(self):
        for invalid in ("", "   ", "x" * 2001):
            with self.assertRaises(ValidationError):
                CareGoalProgressCreate(note=invalid)
        with self.assertRaises(ValidationError):
            CareGoalProgressCreate.model_validate({"note": "Update", "goal_id": 2})


if __name__ == "__main__":
    unittest.main()
