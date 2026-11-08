"""Cancelled follow-up tasks remain in the chart but leave open worklists."""

import unittest
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.follow_up_tasks import (
    cancel_follow_up_task,
    complete_follow_up_task,
    create_follow_up_task,
    list_follow_up_tasks,
    list_open_follow_up_tasks,
)
from backend.models import Base, CareGoal, FollowUpTask, Patient
from backend.schemas import (
    FollowUpTaskCancel,
    FollowUpTaskComplete,
    FollowUpTaskCreate,
    FollowUpTaskRead,
)


class FollowUpCancellationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Avery", last_name="Example",
                date_of_birth=date(1988, 2, 14), sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            goal = CareGoal(patient_id=patient.id, title="Record daily steps")
            session.add(goal)
            session.flush()
            self.patient_id, self.goal_id = patient.id, goal.id
            task = create_follow_up_task(
                session, patient.id,
                FollowUpTaskCreate(
                    title="Call about activity", care_goal_id=goal.id,
                    due_date=date(2026, 11, 15),
                ),
            )
            self.task_id = task.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_cancellation_retains_task_history_and_goal_link(self):
        with Session(self.engine) as session:
            cancelled = cancel_follow_up_task(
                session, self.task_id,
                FollowUpTaskCancel(reason="  Care plan changed  "),
            )
            result = FollowUpTaskRead.model_validate(cancelled)
            self.assertEqual(result.status, "cancelled")
            self.assertEqual(result.cancellation_reason, "Care plan changed")
            self.assertIsNotNone(result.cancelled_at)
            self.assertIsNone(result.completed_at)
            self.assertIsNone(result.completion_note)
            session.commit()

        with Session(self.engine) as session:
            saved = FollowUpTaskRead.model_validate(
                list_follow_up_tasks(session, self.patient_id)[0]
            )
            self.assertEqual(saved.title, "Call about activity")
            self.assertEqual(saved.care_goal_id, self.goal_id)
            self.assertEqual(saved.due_date, date(2026, 11, 15))
            self.assertEqual(saved.status, "cancelled")
            self.assertEqual(saved.cancellation_reason, "Care plan changed")
            self.assertEqual(list_open_follow_up_tasks(session), [])

    def test_closed_tasks_reject_cancellation_or_completion(self):
        with Session(self.engine) as session:
            cancel_follow_up_task(
                session, self.task_id,
                FollowUpTaskCancel(reason="No longer needed"),
            )
            session.commit()

        with Session(self.engine) as session:
            for action in (
                lambda: cancel_follow_up_task(
                    session, self.task_id,
                    FollowUpTaskCancel(reason="Overwrite reason"),
                ),
                lambda: complete_follow_up_task(
                    session, self.task_id,
                    FollowUpTaskComplete(completion_note="Not completed"),
                ),
            ):
                with self.assertRaises(HTTPException) as raised:
                    action()
                self.assertEqual(raised.exception.status_code, 409)
            saved = session.get(FollowUpTask, self.task_id)
            self.assertEqual(saved.cancellation_reason, "No longer needed")

    def test_completed_task_cannot_be_cancelled(self):
        with Session(self.engine) as session:
            complete_follow_up_task(
                session, self.task_id,
                FollowUpTaskComplete(completion_note="Called patient"),
            )
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                cancel_follow_up_task(
                    session, self.task_id,
                    FollowUpTaskCancel(reason="Claim it was not done"),
                )
            self.assertEqual(raised.exception.status_code, 409)
            saved = session.get(FollowUpTask, self.task_id)
            self.assertEqual(saved.status, "completed")
            self.assertIsNone(saved.cancelled_at)

    def test_missing_task_returns_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                cancel_follow_up_task(
                    session, 99999,
                    FollowUpTaskCancel(reason="Missing"),
                )
            self.assertEqual(raised.exception.status_code, 404)

    def test_cancellation_reason_validation(self):
        for reason in ("", "   ", "x" * 2001):
            with self.assertRaises(ValidationError):
                FollowUpTaskCancel(reason=reason)
        with self.assertRaises(ValidationError):
            FollowUpTaskCancel.model_validate(
                {"reason": "Duplicate", "status": "cancelled"}
            )


if __name__ == "__main__":
    unittest.main()
