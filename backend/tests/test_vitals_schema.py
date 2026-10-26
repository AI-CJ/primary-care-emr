"""Validation for synthetic patient vital recordings."""
import unittest
from datetime import date, timedelta

from pydantic import ValidationError

from backend.schemas import VitalCreate


class VitalSchemaTests(unittest.TestCase):
    def test_valid_recording_and_trimmed_notes(self):
        vital = VitalCreate(
            recorded_on=date.today(),
            systolic_bp=120,
            diastolic_bp=80,
            heart_rate=72,
            notes="  Routine visit  ",
        )
        self.assertEqual(vital.notes, "Routine visit")
        self.assertEqual(vital.systolic_bp, 120)

    def test_at_least_one_measurement_required(self):
        with self.assertRaises(ValidationError):
            VitalCreate(recorded_on=date.today(), notes="No readings")

    def test_both_blood_pressure_values_required(self):
        for data in ({"systolic_bp": 120}, {"diastolic_bp": 80}):
            with self.subTest(data=data):
                with self.assertRaises(ValidationError):
                    VitalCreate(recorded_on=date.today(), **data)

    def test_systolic_cannot_be_below_diastolic(self):
        with self.assertRaises(ValidationError):
            VitalCreate(
                recorded_on=date.today(),
                systolic_bp=70,
                diastolic_bp=110,
            )

    def test_future_dates_rejected(self):
        with self.assertRaises(ValidationError):
            VitalCreate(
                recorded_on=date.today() + timedelta(days=1),
                heart_rate=72,
            )

    def test_measurements_outside_limits_rejected(self):
        for data in (
            {"oxygen_saturation": 101},
            {"heart_rate": 0},
            {"temperature_c": float("nan")},
            {"height_cm": -10.0},
        ):
            with self.subTest(data=data):
                with self.assertRaises(ValidationError):
                    VitalCreate(recorded_on=date.today(), **data)


if __name__ == "__main__":
    unittest.main()
