"""Portal allergy summaries exclude staff notes and unrelated patients."""

import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.main import read_portal_preview_allergies
from backend.models import Allergy, Base, Patient
from backend.portal_allergies import list_portal_preview_allergies


class PortalPreviewAllergyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patients = [
                Patient(
                    first_name=name,
                    last_name="Example",
                    date_of_birth=date(1990, 6, 12),
                    sex_at_birth="unknown",
                )
                for name in ("Avery", "Morgan", "Taylor")
            ]
            session.add_all(patients)
            session.flush()
            self.patient_id, other_id, self.empty_id = [p.id for p in patients]
            session.add_all([
                Allergy(
                    patient_id=self.patient_id,
                    allergen="Fictional pollen",
                    severity="mild",
                    status="active",
                    reaction="Sneezing",
                    onset_date=date(2025, 4, 3),
                    notes="Staff-only allergy history",
                ),
                Allergy(
                    patient_id=self.patient_id,
                    allergen="Fictional adhesive",
                    severity="severe",
                    status="active",
                    reaction="Rash",
                ),
                Allergy(
                    patient_id=self.patient_id,
                    allergen="Fictional tablet",
                    severity="unknown",
                    status="inactive",
                    onset_date=date(2024, 9, 8),
                    notes="Private reassessment",
                ),
                Allergy(
                    patient_id=other_id,
                    allergen="Other patient's allergy",
                    severity="unknown",
                    status="active",
                    notes="Other patient's notes",
                ),
            ])
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_active_and_inactive_history(self):
        with Session(self.engine) as session:
            allergies = list_portal_preview_allergies(session, self.patient_id)
        self.assertEqual([item.allergen for item in allergies], [
            "Fictional adhesive", "Fictional pollen", "Fictional tablet",
        ])
        self.assertEqual([item.status for item in allergies], [
            "active", "active", "inactive",
        ])
        self.assertEqual(allergies[0].severity, "severe")
        self.assertEqual(allergies[1].reaction, "Sneezing")
        self.assertEqual(allergies[2].onset_date, date(2024, 9, 8))

    def test_only_displayed_fields_are_returned(self):
        with Session(self.engine) as session:
            allergies = list_portal_preview_allergies(session, self.patient_id)
        allowed = {"id", "allergen", "reaction", "severity", "status", "onset_date"}
        for item in allergies:
            self.assertEqual(set(item.model_dump(mode="json")), allowed)
        self.assertNotIn("Staff-only", repr(allergies))
        self.assertNotIn("Private reassessment", repr(allergies))
        self.assertNotIn("Other patient", repr(allergies))
        self.assertNotIn("patient_id=", repr(allergies))
        self.assertNotIn("notes=", repr(allergies))

    def test_endpoint_returns_limited_summaries(self):
        with patch("backend.main.engine", self.engine):
            allergies = read_portal_preview_allergies(self.patient_id)
        self.assertEqual(len(allergies), 3)
        self.assertEqual(allergies[0].allergen, "Fictional adhesive")

    def test_empty_chart_and_missing_patient(self):
        with Session(self.engine) as session:
            self.assertEqual(list_portal_preview_allergies(session, self.empty_id), [])
            with self.assertRaises(HTTPException) as raised:
                list_portal_preview_allergies(session, 999999)
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
