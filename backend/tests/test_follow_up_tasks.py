"""Patient follow-up tasks remain in the chart after completion."""

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
from backend.models import Base, FollowUpTask, Patient
from backend.schemas import (
    FollowUpTaskComplete,
    FollowUpTaskCreate,
    FollowUpTaskRead,
)


class FollowUpTaskTests(unittest.TestCase):
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

    def test_create_and_list_tasks_by_patient(self):
        with Session(self.engine) as session:
            older = create_follow_up_task(
                session, self.first_id,
                FollowUpTaskCreate(
                    title="  Call about follow-up  ",
                    details="  Discuss next appointment.  ",
                    due_date=date(2026, 11, 12),
                ),
            )
            newer = create_follow_up_task(
                session, self.first_id, FollowUpTaskCreate(title="Review visit summary"),
            )
            other = create_follow_up_task(
                session, self.second_id, FollowUpTaskCreate(title="Another chart"),
            )
            ids = (older.id, newer.id, other.id)
            session.commit()

        with Session(self.engine) as session:
            tasks = list_follow_up_tasks(session, self.first_id)
            self.assertEqual([task.id for task in tasks], [ids[1], ids[0]])
            saved = FollowUpTaskRead.model_validate(tasks[1])
            self.assertEqual(saved.title, "Call about follow-up")
            self.assertEqual(saved.details, "Discuss next appointment.")
            self.assertEqual(saved.due_date, date(2026, 11, 12))
            self.assertEqual(saved.status, "open")
            self.assertIsNone(saved.completed_at)
            self.assertEqual(
                [task.id for task in list_follow_up_tasks(session, self.second_id)],
                [ids[2]],
            )

    def test_completion_preserves_original_task_and_outcome(self):
        with Session(self.engine) as session:
            task = create_follow_up_task(
                session, self.first_id, FollowUpTaskCreate(title="Arrange follow-up")
            )
            task_id = task.id
            session.commit()

        with Session(self.engine) as session:
            completed = complete_follow_up_task(
                session, task_id,
                FollowUpTaskComplete(completion_note="  Scheduled for next week.  "),
            )
            self.assertEqual(completed.status, "completed")
            self.assertEqual(completed.completion_note, "Scheduled for next week.")
            self.assertIsNotNone(completed.completed_at)
            session.commit()

        with Session(self.engine) as session:
            saved = FollowUpTaskRead.model_validate(
                list_follow_up_tasks(session, self.first_id)[0]
            )
            self.assertEqual(saved.title, "Arrange follow-up")
            self.assertEqual(saved.status, "completed")
            self.assertEqual(saved.completion_note, "Scheduled for next week.")
            self.assertIsNotNone(saved.completed_at)

    def test_completed_task_cannot_be_completed_again(self):
        with Session(self.engine) as session:
            task = create_follow_up_task(
                session, self.first_id, FollowUpTaskCreate(title="Call patient")
            )
            task_id = task.id
            complete_follow_up_task(
                session, task_id,
                FollowUpTaskComplete(completion_note="Call completed"),
            )
            session.commit()

        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                complete_follow_up_task(
                    session, task_id,
                    FollowUpTaskComplete(completion_note="Overwrite"),
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(
                session.get(FollowUpTask, task_id).completion_note,
                "Call completed",
            )

    def test_missing_patient_or_task_returns_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                list_follow_up_tasks(session, 99999)
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                create_follow_up_task(
                    session, 99999, FollowUpTaskCreate(title="Orphan task"),
                )
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                complete_follow_up_task(
                    session, 99999, FollowUpTaskComplete(completion_note="Missing"),
                )
            self.assertEqual(raised.exception.status_code, 404)

    def test_validation_rejects_blank_oversized_or_extra_fields(self):
        for title in ("", "   ", "x" * 201):
            with self.assertRaises(ValidationError):
                FollowUpTaskCreate(title=title)
        with self.assertRaises(ValidationError):
            FollowUpTaskCreate(title="Test", details="x" * 2001)
        for note in ("", "   ", "x" * 2001):
            with self.assertRaises(ValidationError):
                FollowUpTaskComplete(completion_note=note)
        with self.assertRaises(ValidationError):
            FollowUpTaskCreate.model_validate({"title": "Test", "patient_id": self.first_id})
        with self.assertRaises(ValidationError):
            FollowUpTaskComplete.model_validate({"completion_note": "Done", "status": "open"})

    def test_optional_details_are_normalized(self):
        self.assertIsNone(FollowUpTaskCreate(title="Test", details="   ").details)


if __name__ == "__main__":
    unittest.main()
