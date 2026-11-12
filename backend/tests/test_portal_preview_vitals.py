"""The portal preview returns only recent measurements, without staff notes."""

import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.main import read_portal_preview_vitals
from backend.models import Base, Patient, Vital
from backend.portal_vitals import list_portal_preview_vitals


class PortalPreviewVitalTests(unittest.TestCase):
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
                Vital(
                    patient_id=self.patient_id, recorded_on=date(2026, 9, 1),
                    heart_rate=66, notes="Old private note",
                ),
                Vital(
                    patient_id=self.patient_id, recorded_on=date(2026, 10, 1),
                    systolic_bp=120, diastolic_bp=80,
                    notes="Private assessment",
                ),
                Vital(
                    patient_id=self.patient_id, recorded_on=date(2026, 11, 1),
                    oxygen_saturation=98, notes="Staff-only observation",
                ),
                Vital(
                    patient_id=self.patient_id, recorded_on=date(2026, 11, 1),
                    height_cm=180.0, weight_kg=82.5,
                ),
                Vital(
                    patient_id=other_id, recorded_on=date(2026, 11, 2),
                    heart_rate=99, notes="Other patient's note",
                ),
            ])
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_latest_three_with_stable_order(self):
        with Session(self.engine) as session:
            records = list_portal_preview_vitals(session, self.patient_id)

        self.assertEqual(
            [item.recorded_on for item in records],
            [date(2026, 11, 1), date(2026, 11, 1), date(2026, 10, 1)],
        )
        self.assertEqual(records[0].weight_kg, 82.5)
        self.assertEqual(records[1].oxygen_saturation, 98)
        self.assertEqual(records[2].systolic_bp, 120)

    def test_response_excludes_notes_and_other_patients(self):
        with Session(self.engine) as session:
            records = list_portal_preview_vitals(session, self.patient_id)

        allowed = {
            "id", "recorded_on", "systolic_bp", "diastolic_bp",
            "heart_rate", "respiratory_rate", "temperature_c",
            "oxygen_saturation", "height_cm", "weight_kg",
        }
        for item in records:
            self.assertEqual(set(item.model_dump(mode="json")), allowed)
        serialized = repr(records)
        for private_value in (
            "Private assessment", "Staff-only observation", "Other patient",
            "patient_id=", "notes=",
        ):
            self.assertNotIn(private_value, serialized)

    def test_endpoint_returns_limited_measurements(self):
        with patch("backend.main.engine", self.engine):
            records = read_portal_preview_vitals(self.patient_id)
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].weight_kg, 82.5)

    def test_empty_chart_and_missing_patient(self):
        with Session(self.engine) as session:
            self.assertEqual(list_portal_preview_vitals(session, self.empty_id), [])
            with self.assertRaises(HTTPException) as raised:
                list_portal_preview_vitals(session, 999999)
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
