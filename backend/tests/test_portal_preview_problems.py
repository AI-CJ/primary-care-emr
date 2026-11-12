"""The portal problem summary excludes private notes and other charts."""

import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.main import read_portal_preview_problems
from backend.models import Base, Patient, Problem
from backend.portal_problems import list_portal_preview_problems


class PortalPreviewProblemTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patients = [
                Patient(
                    first_name=name,
                    last_name="Example",
                    date_of_birth=date(1991, 4, 12),
                    sex_at_birth="unknown",
                )
                for name in ("Avery", "Morgan", "Taylor")
            ]
            session.add_all(patients)
            session.flush()
            self.patient_id, other_id, self.empty_id = [p.id for p in patients]
            session.add_all([
                Problem(
                    patient_id=self.patient_id,
                    name="Fictional asthma",
                    status="active",
                    onset_date=date(2026, 1, 1),
                    notes="Staff-only clinical note",
                ),
                Problem(
                    patient_id=self.patient_id,
                    name="Fictional migraine",
                    status="active",
                ),
                Problem(
                    patient_id=self.patient_id,
                    name="Fictional sprain",
                    status="resolved",
                    onset_date=date(2026, 5, 4),
                    resolved_date=date(2026, 7, 12),
                    notes="Private resolution details",
                ),
                Problem(
                    patient_id=other_id,
                    name="Other patient's condition",
                    status="active",
                    notes="Another private note",
                ),
            ])
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_active_and_resolved_history_is_preserved(self):
        with Session(self.engine) as session:
            problems = list_portal_preview_problems(session, self.patient_id)

        self.assertEqual(
            [p.name for p in problems],
            ["Fictional asthma", "Fictional migraine", "Fictional sprain"],
        )
        self.assertEqual([p.status for p in problems], ["active", "active", "resolved"])
        self.assertEqual(problems[0].onset_date, date(2026, 1, 1))
        self.assertEqual(problems[2].resolved_date, date(2026, 7, 12))

    def test_only_display_fields_are_returned(self):
        with Session(self.engine) as session:
            problems = list_portal_preview_problems(session, self.patient_id)

        for problem in problems:
            self.assertEqual(
                set(problem.model_dump(mode="json")),
                {"id", "name", "status", "onset_date", "resolved_date"},
            )
        self.assertNotIn("Staff-only", repr(problems))
        self.assertNotIn("Private resolution", repr(problems))
        self.assertNotIn("Other patient", repr(problems))
        self.assertNotIn("patient_id=", repr(problems))
        self.assertNotIn("notes=", repr(problems))

    def test_endpoint_returns_patient_facing_summary(self):
        with patch("backend.main.engine", self.engine):
            problems = read_portal_preview_problems(self.patient_id)
        self.assertEqual(len(problems), 3)
        self.assertEqual(problems[0].name, "Fictional asthma")

    def test_empty_chart_and_unknown_patient(self):
        with Session(self.engine) as session:
            self.assertEqual(list_portal_preview_problems(session, self.empty_id), [])
            with self.assertRaises(HTTPException) as raised:
                list_portal_preview_problems(session, 999999)
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
