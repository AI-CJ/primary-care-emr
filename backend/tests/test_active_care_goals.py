"""Active care goals remain visible for clinic-wide follow-up."""

import unittest
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.care_goals import (
    complete_care_goal,
    create_care_goal,
    discontinue_care_goal,
    list_active_care_goals,
    list_care_goals,
)
from backend.models import Base, CareGoal, Patient
from backend.schemas import (
    ActiveCareGoalRead,
    CareGoalComplete,
    CareGoalCreate,
    CareGoalDiscontinue,
    CareGoalRead,
)


class ActiveCareGoalWorklistTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        today = date.today()
        self.today = today

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
            self.first_patient_id, self.second_patient_id = first.id, second.id

            cases = [
                ("Later", today + timedelta(days=5), "active", first.id),
                ("No target", None, "active", second.id),
                ("Overdue one", today - timedelta(days=5), "active", second.id),
                ("Overdue two", today - timedelta(days=5), "active", first.id),
                ("Due today", today, "active", first.id),
                ("Already completed", today - timedelta(days=12), "completed", first.id),
                ("Discontinued", today - timedelta(days=9), "discontinued", second.id),
            ]
            for index, (title, target, status, patient_id) in enumerate(cases):
                session.add(CareGoal(
                    patient_id=patient_id, title=title,
                    target_date=target, status=status,
                    created_at=datetime(2026, 11, 1, 9 + index, tzinfo=timezone.utc),
                ))
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_active_goals_sorted_by_target_then_creation(self):
        with Session(self.engine) as session:
            rows = list_active_care_goals(session)
            self.assertEqual(
                [goal.title for goal, _ in rows],
                ["Overdue one", "Overdue two", "Due today", "Later", "No target"],
            )
            self.assertTrue(all(goal.status == "active" for goal, _ in rows))
            self.assertEqual(rows[0][1].id, self.second_patient_id)
            self.assertEqual(rows[4][1].id, self.second_patient_id)

    def test_read_schema_includes_patient_name_and_overdue_cutoff(self):
        with Session(self.engine) as session:
            entries = [
                ActiveCareGoalRead(
                    **CareGoalRead.model_validate(goal).model_dump(),
                    patient_name=f"{patient.preferred_name or patient.first_name} {patient.last_name}",
                    is_overdue=goal.target_date is not None and goal.target_date < self.today,
                )
                for goal, patient in list_active_care_goals(session)
            ]
        self.assertEqual(entries[0].patient_name, "Mo Sample")
        self.assertEqual(entries[0].patient_id, self.second_patient_id)
        self.assertEqual(
            [entry.is_overdue for entry in entries],
            [True, True, False, False, False],
        )
        self.assertIsNone(entries[-1].target_date)

    def test_closed_goals_leave_worklist_without_losing_history(self):
        with Session(self.engine) as session:
            rows = list_active_care_goals(session)
            complete_care_goal(
                session, rows[0][0].id,
                CareGoalComplete(completion_note="Synthetic target met"),
            )
            discontinue_care_goal(
                session, rows[1][0].id,
                CareGoalDiscontinue(reason="Synthetic plan changed"),
            )
            session.commit()

        with Session(self.engine) as session:
            self.assertEqual(
                [goal.title for goal, _ in list_active_care_goals(session)],
                ["Due today", "Later", "No target"],
            )
            historical = list_care_goals(session, self.second_patient_id)
            self.assertTrue(any(goal.status == "completed" for goal in historical))
            self.assertTrue(any(goal.status == "discontinued" for goal in historical))

    def test_new_active_goal_is_available_without_target_date(self):
        with Session(self.engine) as session:
            new = create_care_goal(
                session, self.first_patient_id,
                CareGoalCreate(title="Try a new synthetic care plan"),
            )
            new_id = new.id
            session.commit()

        with Session(self.engine) as session:
            goals = list_active_care_goals(session)
            self.assertEqual(goals[-1][0].id, new_id)
            self.assertIsNone(goals[-1][0].target_date)


if __name__ == "__main__":
    unittest.main()
