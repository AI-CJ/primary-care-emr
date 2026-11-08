"""Rescheduling open follow-ups preserves a readable due-date history."""

import unittest
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.follow_up_tasks import (
    complete_follow_up_task,
    list_follow_up_due_date_changes,
    list_follow_up_tasks,
    list_open_follow_up_tasks,
    reschedule_follow_up_task,
)
from backend.models import Base, FollowUpTask, Patient
from backend.schemas import (
    FollowUpDueDateChangeRead,
    FollowUpTaskComplete,
    FollowUpTaskRead,
    FollowUpTaskReschedule,
)


class FollowUpDueDateChangeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Avery", last_name="Example",
                date_of_birth=date(1988, 2, 14), sex_at_birth="unknown",
            )
            other = Patient(
                first_name="Morgan", last_name="Sample",
                date_of_birth=date(1991, 6, 21), sex_at_birth="unknown",
            )
            session.add_all([patient, other])
            session.flush()
            first = FollowUpTask(
                patient_id=patient.id, title="Review synthetic lab follow-up",
                due_date=date(2026, 11, 10), status="open",
            )
            second = FollowUpTask(
                patient_id=other.id, title="Unrelated task",
                due_date=None, status="open",
            )
            session.add_all([first, second])
            session.flush()
            self.patient_id, self.first_id, self.other_id = (
                patient.id, first.id, second.id,
            )
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_rescheduling_records_both_dates_and_reason(self):
        with Session(self.engine) as session:
            updated = reschedule_follow_up_task(
                session, self.first_id,
                FollowUpTaskReschedule(
                    due_date=date(2026, 11, 14),
                    reason="  Awaiting a synthetic result  ",
                ),
            )
            self.assertEqual(updated.due_date, date(2026, 11, 14))
            self.assertEqual(updated.status, "open")
            session.commit()

        with Session(self.engine) as session:
            record = list_follow_up_due_date_changes(session, self.first_id)[0]
            serialized = FollowUpDueDateChangeRead.model_validate(record)
            self.assertEqual(serialized.previous_due_date, date(2026, 11, 10))
            self.assertEqual(serialized.new_due_date, date(2026, 11, 14))
            self.assertEqual(serialized.reason, "Awaiting a synthetic result")
            self.assertIsNotNone(serialized.changed_at)
            chart_task = list_follow_up_tasks(session, self.patient_id)[0]
            self.assertEqual(
                FollowUpTaskRead.model_validate(chart_task).due_date,
                date(2026, 11, 14),
            )
            self.assertEqual(len(list_open_follow_up_tasks(session)), 2)

    def test_multiple_changes_and_cleared_deadline_are_preserved(self):
        with Session(self.engine) as session:
            reschedule_follow_up_task(
                session, self.first_id,
                FollowUpTaskReschedule(due_date=None, reason="No firm deadline"),
            )
            session.commit()
            reschedule_follow_up_task(
                session, self.first_id,
                FollowUpTaskReschedule(
                    due_date=date(2026, 11, 21), reason="New target agreed",
                ),
            )
            session.commit()

        with Session(self.engine) as session:
            changes = list_follow_up_due_date_changes(session, self.first_id)
            self.assertEqual(
                [(change.previous_due_date, change.new_due_date) for change in changes],
                [(date(2026, 11, 10), None), (None, date(2026, 11, 21))],
            )
            self.assertEqual(session.get(FollowUpTask, self.first_id).due_date,
                             date(2026, 11, 21))

    def test_unchanged_due_date_is_rejected_without_history(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                reschedule_follow_up_task(
                    session, self.first_id,
                    FollowUpTaskReschedule(
                        due_date=date(2026, 11, 10), reason="Unchanged",
                    ),
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(list_follow_up_due_date_changes(session, self.first_id), [])

    def test_completed_or_cancelled_tasks_cannot_be_rescheduled(self):
        with Session(self.engine) as session:
            complete_follow_up_task(
                session, self.first_id,
                FollowUpTaskComplete(completion_note="Follow-up completed"),
            )
            session.get(FollowUpTask, self.other_id).status = "cancelled"
            session.commit()

        with Session(self.engine) as session:
            for task_id in (self.first_id, self.other_id):
                with self.assertRaises(HTTPException) as raised:
                    reschedule_follow_up_task(
                        session, task_id,
                        FollowUpTaskReschedule(
                            due_date=date(2026, 11, 19), reason="Too late",
                        ),
                    )
                self.assertEqual(raised.exception.status_code, 409)
                self.assertEqual(list_follow_up_due_date_changes(session, task_id), [])

    def test_missing_task_returns_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                reschedule_follow_up_task(
                    session, 999999,
                    FollowUpTaskReschedule(due_date=None, reason="Missing"),
                )
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                list_follow_up_due_date_changes(session, 999999)
            self.assertEqual(raised.exception.status_code, 404)

    def test_history_is_restricted_to_the_selected_task(self):
        with Session(self.engine) as session:
            reschedule_follow_up_task(
                session, self.first_id,
                FollowUpTaskReschedule(due_date=None, reason="Rescheduled"),
            )
            session.commit()
        with Session(self.engine) as session:
            self.assertEqual(len(list_follow_up_due_date_changes(session, self.first_id)), 1)
            self.assertEqual(list_follow_up_due_date_changes(session, self.other_id), [])

    def test_validation_requires_explicit_date_and_reason(self):
        bad_inputs = [
            {"reason": "Date omitted"},
            {"due_date": None, "reason": " "},
            {"due_date": None, "reason": "x" * 2001},
            {"due_date": None, "reason": "Reason", "status": "open"},
        ]
        for payload in bad_inputs:
            with self.subTest(payload=payload):
                with self.assertRaises(ValidationError):
                    FollowUpTaskReschedule.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
