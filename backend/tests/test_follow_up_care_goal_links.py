"""Follow-up tasks may be linked only to active goals in the same patient chart."""

import unittest
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.follow_up_tasks import (
    complete_follow_up_task,
    create_follow_up_task,
    list_follow_up_tasks,
)
from backend.models import Base, CareGoal, FollowUpTask, Patient
from backend.schemas import (
    FollowUpTaskComplete,
    FollowUpTaskCreate,
    FollowUpTaskRead,
)


class FollowUpCareGoalLinkTests(unittest.TestCase):
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
            goals = [
                CareGoal(patient_id=first.id, title="Track daily activity"),
                CareGoal(patient_id=second.id, title="Other patient's goal"),
                CareGoal(patient_id=first.id, title="Already achieved", status="completed"),
                CareGoal(patient_id=first.id, title="Stopped", status="discontinued"),
            ]
            session.add_all(goals)
            session.flush()
            self.goal_ids = [goal.id for goal in goals]
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_active_goal_can_be_linked_to_task(self):
        with Session(self.engine) as session:
            task = create_follow_up_task(
                session, self.first_id,
                FollowUpTaskCreate(title="Call about exercise", care_goal_id=self.goal_ids[0]),
            )
            saved = FollowUpTaskRead.model_validate(task)
            self.assertEqual(saved.care_goal_id, self.goal_ids[0])
            session.commit()

        with Session(self.engine) as session:
            tasks = list_follow_up_tasks(session, self.first_id)
            self.assertEqual(tasks[0].care_goal_id, self.goal_ids[0])

    def test_unlinked_task_remains_supported(self):
        with Session(self.engine) as session:
            task = create_follow_up_task(
                session, self.first_id, FollowUpTaskCreate(title="Schedule follow-up")
            )
            self.assertIsNone(FollowUpTaskRead.model_validate(task).care_goal_id)

    def test_other_patients_goal_is_not_exposed_or_linked(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_follow_up_task(
                    session, self.first_id,
                    FollowUpTaskCreate(title="Wrong chart", care_goal_id=self.goal_ids[1]),
                )
            self.assertEqual(raised.exception.status_code, 404)
            self.assertEqual(session.query(FollowUpTask).count(), 0)

    def test_nonexistent_goal_returns_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_follow_up_task(
                    session, self.first_id,
                    FollowUpTaskCreate(title="Missing goal", care_goal_id=99999),
                )
            self.assertEqual(raised.exception.status_code, 404)

    def test_closed_goals_cannot_receive_new_tasks(self):
        with Session(self.engine) as session:
            for goal_id in self.goal_ids[2:]:
                with self.assertRaises(HTTPException) as raised:
                    create_follow_up_task(
                        session, self.first_id,
                        FollowUpTaskCreate(title="Too late", care_goal_id=goal_id),
                    )
                self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(session.query(FollowUpTask).count(), 0)

    def test_completion_does_not_erase_the_goal_link(self):
        with Session(self.engine) as session:
            task = create_follow_up_task(
                session, self.first_id,
                FollowUpTaskCreate(title="Check progress", care_goal_id=self.goal_ids[0]),
            )
            task_id = task.id
            complete_follow_up_task(
                session, task_id,
                FollowUpTaskComplete(completion_note="Progress discussed"),
            )
            session.commit()

        with Session(self.engine) as session:
            saved = FollowUpTaskRead.model_validate(session.get(FollowUpTask, task_id))
            self.assertEqual(saved.status, "completed")
            self.assertEqual(saved.care_goal_id, self.goal_ids[0])

    def test_invalid_goal_ids_are_rejected(self):
        for goal_id in (0, -1):
            with self.assertRaises(ValidationError):
                FollowUpTaskCreate(title="Invalid", care_goal_id=goal_id)


if __name__ == "__main__":
    unittest.main()
