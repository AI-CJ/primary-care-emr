"""Discontinued care goals retain their clinical history without recording success."""

import unittest
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.care_goals import (
    complete_care_goal,
    create_care_goal,
    discontinue_care_goal,
    list_care_goals,
    list_goal_progress,
    record_goal_progress,
)
from backend.models import Base, CareGoal, Patient
from backend.schemas import (
    CareGoalComplete,
    CareGoalCreate,
    CareGoalDiscontinue,
    CareGoalProgressCreate,
    CareGoalRead,
)


class CareGoalDiscontinuationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Jamie", last_name="Example",
                date_of_birth=date(1985, 6, 20), sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            self.patient_id = patient.id
            self.goal_id = create_care_goal(
                session, patient.id,
                CareGoalCreate(title="Practice daily stretching"),
            ).id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_discontinuation_keeps_goal_and_progress_without_claiming_success(self):
        with Session(self.engine) as session:
            entry = record_goal_progress(
                session, self.goal_id,
                CareGoalProgressCreate(note="Practiced twice last week."),
            )
            progress_id = entry.id
            goal = discontinue_care_goal(
                session, self.goal_id,
                CareGoalDiscontinue(reason="  Changed the care plan.  "),
            )
            result = CareGoalRead.model_validate(goal)
            session.commit()

        self.assertEqual(result.status, "discontinued")
        self.assertEqual(result.title, "Practice daily stretching")
        self.assertEqual(result.discontinuation_reason, "Changed the care plan.")
        self.assertIsNotNone(result.discontinued_at)
        self.assertIsNone(result.completed_at)
        self.assertIsNone(result.completion_note)

        with Session(self.engine) as session:
            self.assertEqual(
                [item.id for item in list_goal_progress(session, self.goal_id)],
                [progress_id],
            )
            self.assertEqual(
                list_care_goals(session, self.patient_id)[0].status,
                "discontinued",
            )
            for action in (
                lambda: complete_care_goal(
                    session, self.goal_id,
                    CareGoalComplete(completion_note="Not actually completed"),
                ),
                lambda: record_goal_progress(
                    session, self.goal_id,
                    CareGoalProgressCreate(note="Late update"),
                ),
                lambda: discontinue_care_goal(
                    session, self.goal_id,
                    CareGoalDiscontinue(reason="Overwrite history"),
                ),
            ):
                with self.assertRaises(HTTPException) as raised:
                    action()
                self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(
                session.get(CareGoal, self.goal_id).discontinuation_reason,
                "Changed the care plan.",
            )

    def test_completed_goal_cannot_be_discontinued(self):
        with Session(self.engine) as session:
            complete_care_goal(
                session, self.goal_id,
                CareGoalComplete(completion_note="Goal achieved"),
            )
            session.commit()

        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                discontinue_care_goal(
                    session, self.goal_id,
                    CareGoalDiscontinue(reason="Not pursued"),
                )
            self.assertEqual(raised.exception.status_code, 409)
            saved = session.get(CareGoal, self.goal_id)
            self.assertEqual(saved.status, "completed")
            self.assertIsNone(saved.discontinued_at)

    def test_missing_goal_returns_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                discontinue_care_goal(
                    session, 999999,
                    CareGoalDiscontinue(reason="No goal"),
                )
            self.assertEqual(raised.exception.status_code, 404)

    def test_discontinuation_reason_requires_meaningful_text(self):
        for reason in ("", "   ", "x" * 2001):
            with self.assertRaises(ValidationError):
                CareGoalDiscontinue(reason=reason)
        with self.assertRaises(ValidationError):
            CareGoalDiscontinue.model_validate(
                {"reason": "Changed plan", "status": "completed"}
            )


if __name__ == "__main__":
    unittest.main()
