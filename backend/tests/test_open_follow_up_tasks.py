"""Outstanding patient follow-up tasks appear in the clinic worklist."""

import unittest
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.follow_up_tasks import (
    complete_follow_up_task,
    create_follow_up_task,
    list_follow_up_tasks,
    list_open_follow_up_tasks,
)
from backend.models import Base, FollowUpTask, Patient
from backend.schemas import (
    FollowUpTaskComplete,
    FollowUpTaskCreate,
    FollowUpTaskRead,
    OpenFollowUpTaskRead,
)


class OpenFollowUpTaskTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.today = date.today()

        with Session(self.engine) as session:
            first = Patient(
                first_name="Avery", last_name="Example",
                date_of_birth=date(1988, 2, 14), sex_at_birth="unknown",
            )
            second = Patient(
                first_name="Morgan", preferred_name="Mo", last_name="Sample",
                date_of_birth=date(1991, 6, 21), sex_at_birth="unknown",
            )
            session.add_all([first, second])
            session.flush()
            self.first_id, self.second_id = first.id, second.id

            cases = [
                ("Later", self.today + timedelta(days=4), "open", first.id),
                ("No deadline", None, "open", second.id),
                ("Overdue first", self.today - timedelta(days=4), "open", second.id),
                ("Overdue second", self.today - timedelta(days=4), "open", first.id),
                ("Due today", self.today, "open", first.id),
                ("Completed past-due", self.today - timedelta(days=12), "completed", second.id),
            ]
            for index, (title, due, status, patient_id) in enumerate(cases):
                session.add(FollowUpTask(
                    patient_id=patient_id, title=title, due_date=due,
                    status=status,
                    created_at=datetime(2026, 11, 1, 9 + index, tzinfo=timezone.utc),
                ))
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_open_tasks_ordered_by_due_date_and_creation(self):
        with Session(self.engine) as session:
            rows = list_open_follow_up_tasks(session)
            self.assertEqual(
                [task.title for task, _ in rows],
                ["Overdue first", "Overdue second", "Due today", "Later", "No deadline"],
            )
            self.assertTrue(all(task.status == "open" for task, _ in rows))
            self.assertEqual(rows[0][1].id, self.second_id)

    def test_read_schema_includes_patient_and_overdue_flag(self):
        with Session(self.engine) as session:
            entries = [
                OpenFollowUpTaskRead(
                    **FollowUpTaskRead.model_validate(task).model_dump(),
                    patient_name=f"{patient.preferred_name or patient.first_name} {patient.last_name}",
                    is_overdue=task.due_date is not None and task.due_date < self.today,
                )
                for task, patient in list_open_follow_up_tasks(session)
            ]
        self.assertEqual(entries[0].patient_name, "Mo Sample")
        self.assertEqual(entries[0].patient_id, self.second_id)
        self.assertEqual(
            [entry.is_overdue for entry in entries],
            [True, True, False, False, False],
        )

    def test_completion_removes_task_from_worklist_but_keeps_chart_history(self):
        with Session(self.engine) as session:
            task_id = next(
                task.id for task, _ in list_open_follow_up_tasks(session)
                if task.title == "Overdue first"
            )
            complete_follow_up_task(
                session, task_id,
                FollowUpTaskComplete(completion_note="Synthetic follow-up complete"),
            )
            session.commit()

        with Session(self.engine) as session:
            self.assertNotIn(
                task_id,
                [task.id for task, _ in list_open_follow_up_tasks(session)],
            )
            saved = next(
                task for task in list_follow_up_tasks(session, self.second_id)
                if task.id == task_id
            )
            self.assertEqual(saved.status, "completed")
            self.assertEqual(saved.completion_note, "Synthetic follow-up complete")

    def test_new_undated_task_is_visible(self):
        with Session(self.engine) as session:
            task = create_follow_up_task(
                session, self.first_id,
                FollowUpTaskCreate(title="Review synthetic visit summary"),
            )
            task_id = task.id
            session.commit()

        with Session(self.engine) as session:
            rows = list_open_follow_up_tasks(session)
            self.assertEqual(rows[-1][0].id, task_id)
            self.assertIsNone(rows[-1][0].due_date)


if __name__ == "__main__":
    unittest.main()
