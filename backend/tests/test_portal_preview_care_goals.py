"""Portal care goals retain status history without staff completion notes."""

import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.main import read_portal_preview_care_goals
from backend.models import Base, CareGoal, Patient
from backend.portal_care_goals import list_portal_preview_care_goals


class PortalPreviewCareGoalTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patients = [
                Patient(
                    first_name=name, last_name="Example",
                    date_of_birth=date(1990, 6, 12), sex_at_birth="unknown",
                )
                for name in ("Avery", "Morgan", "Taylor")
            ]
            session.add_all(patients)
            session.flush()
            self.patient_id, other_id, self.empty_id = [p.id for p in patients]
            session.add_all([
                CareGoal(
                    patient_id=self.patient_id, title="Walk after lunch",
                    status="active", target_date=date(2027, 1, 15),
                    created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                ),
                CareGoal(
                    patient_id=self.patient_id, title="Track daily walks",
                    status="completed", completion_note="Private clinician assessment",
                    completed_at=datetime(2026, 11, 3, tzinfo=timezone.utc),
                    created_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
                ),
                CareGoal(
                    patient_id=self.patient_id, title="Old exercise target",
                    status="discontinued", discontinuation_reason="Private staff rationale",
                    discontinued_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
                    created_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
                ),
                CareGoal(
                    patient_id=other_id, title="Other patient goal",
                    status="active", created_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
                ),
            ])
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_status_history_and_order(self):
        with Session(self.engine) as session:
            goals = list_portal_preview_care_goals(session, self.patient_id)
        self.assertEqual(
            [g.title for g in goals],
            ["Old exercise target", "Track daily walks", "Walk after lunch"],
        )
        self.assertEqual([g.status for g in goals], ["discontinued", "completed", "active"])
        self.assertEqual(goals[0].discontinued_at.date(), date(2026, 11, 4))
        self.assertEqual(goals[1].completed_at.date(), date(2026, 11, 3))
        self.assertEqual(goals[2].target_date, date(2027, 1, 15))

    def test_staff_notes_and_other_charts_are_excluded(self):
        with Session(self.engine) as session:
            goals = list_portal_preview_care_goals(session, self.patient_id)
        expected = {
            "id", "title", "target_date", "status", "created_at",
            "completed_at", "discontinued_at",
        }
        for goal in goals:
            self.assertEqual(set(goal.model_dump(mode="json")), expected)
        serialized = repr(goals)
        for secret in (
            "Private clinician assessment", "Private staff rationale",
            "Other patient goal", "patient_id=", "completion_note=",
        ):
            self.assertNotIn(secret, serialized)

    def test_endpoint_returns_portal_fields(self):
        with patch("backend.main.engine", self.engine):
            goals = read_portal_preview_care_goals(self.patient_id)
        self.assertEqual(len(goals), 3)
        self.assertEqual(goals[0].status, "discontinued")

    def test_empty_and_missing_patient(self):
        with Session(self.engine) as session:
            self.assertEqual(list_portal_preview_care_goals(session, self.empty_id), [])
            with self.assertRaises(HTTPException) as error:
                list_portal_preview_care_goals(session, 999999)
        self.assertEqual(error.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
