"""Portal medication summaries omit staff-only fields and other patients."""

import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.main import read_portal_preview_medications
from backend.models import Base, Medication, Patient
from backend.portal_medications import list_portal_preview_medications


class PortalPreviewMedicationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patients = [
                Patient(
                    first_name=first, last_name="Example",
                    date_of_birth=date(1990, 4, 8), sex_at_birth="unknown",
                )
                for first in ("Avery", "Morgan", "Taylor")
            ]
            session.add_all(patients)
            session.flush()
            self.patient_id, other_id, self.empty_id = [person.id for person in patients]
            session.add_all([
                Medication(
                    patient_id=self.patient_id, name="Fictional vitamin",
                    status="active", strength="100 mg", dose="One tablet",
                    route="Oral", frequency="Daily", start_date=date(2026, 9, 1),
                    instructions="Take with breakfast",
                ),
                Medication(
                    patient_id=self.patient_id, name="Fictional ointment",
                    status="completed", route="Topical",
                    start_date=date(2026, 7, 1), end_date=date(2026, 8, 1),
                ),
                Medication(
                    patient_id=self.patient_id, name="Fictional drops",
                    status="discontinued", end_date=date(2026, 10, 3),
                ),
                Medication(
                    patient_id=other_id, name="Other patient medication",
                    status="active", instructions="Private instructions",
                ),
            ])
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_preserves_active_and_historical_medications(self):
        with Session(self.engine) as session:
            records = list_portal_preview_medications(session, self.patient_id)

        self.assertEqual([item.name for item in records], [
            "Fictional vitamin", "Fictional ointment", "Fictional drops",
        ])
        self.assertEqual([item.status for item in records], [
            "active", "completed", "discontinued",
        ])
        self.assertEqual(records[0].instructions, "Take with breakfast")
        self.assertEqual(records[0].dose, "One tablet")
        self.assertEqual(records[1].end_date, date(2026, 8, 1))

    def test_response_contains_only_portal_fields(self):
        with Session(self.engine) as session:
            records = list_portal_preview_medications(session, self.patient_id)

        allowed = {
            "id", "name", "strength", "dose", "frequency", "status",
            "start_date", "end_date", "instructions",
        }
        for record in records:
            self.assertEqual(set(record.model_dump(mode="json")), allowed)
        self.assertNotIn("Other patient", repr(records))
        self.assertNotIn("Private instructions", repr(records))
        self.assertNotIn("route=", repr(records))
        self.assertNotIn("patient_id=", repr(records))

    def test_endpoint_returns_limited_medication_summaries(self):
        with patch("backend.main.engine", self.engine):
            records = read_portal_preview_medications(self.patient_id)
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].name, "Fictional vitamin")

    def test_empty_chart_and_missing_patient(self):
        with Session(self.engine) as session:
            self.assertEqual(list_portal_preview_medications(session, self.empty_id), [])
            with self.assertRaises(HTTPException) as raised:
                list_portal_preview_medications(session, 999999)
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
