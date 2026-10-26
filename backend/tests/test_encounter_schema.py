"""Validation of synthetic patient visit notes."""
import unittest
from datetime import date, timedelta

from pydantic import ValidationError

from backend.schemas import EncounterCreate


class EncounterSchemaTests(unittest.TestCase):
    def test_accepts_valid_note_and_trims_whitespace(self):
        encounter = EncounterCreate(
            visit_date=date.today(),
            reason_for_visit="  Follow-up  ",
            subjective="  Patient reports improvement.  ",
            assessment=" ",
        )
        self.assertEqual(encounter.reason_for_visit, "Follow-up")
        self.assertEqual(encounter.subjective, "Patient reports improvement.")
        self.assertIsNone(encounter.assessment)

    def test_rejects_blank_reason(self):
        with self.assertRaises(ValidationError):
            EncounterCreate(
                visit_date=date.today(),
                reason_for_visit="   ",
                plan="Follow up next month",
            )

    def test_requires_at_least_one_note_section(self):
        with self.assertRaises(ValidationError):
            EncounterCreate(
                visit_date=date.today(),
                reason_for_visit="Annual visit",
                subjective=" \t ",
            )

    def test_rejects_future_visit_date(self):
        with self.assertRaises(ValidationError):
            EncounterCreate(
                visit_date=date.today() + timedelta(days=1),
                reason_for_visit="Follow-up",
                assessment="Stable",
            )

    def test_limits_text_length(self):
        for data in (
            {"reason_for_visit": "X" * 201, "plan": "Return as needed"},
            {"reason_for_visit": "Follow-up", "subjective": "X" * 4001},
        ):
            with self.subTest(data=data.keys()):
                with self.assertRaises(ValidationError):
                    EncounterCreate(
                        visit_date=date.today(),
                        **data,
                    )


if __name__ == "__main__":
    unittest.main()
