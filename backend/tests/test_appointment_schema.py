"""Validation for synthetic patient appointment scheduling."""
import unittest
from datetime import date, time, timedelta

from pydantic import ValidationError

from backend.schemas import AppointmentCreate


class AppointmentSchemaTests(unittest.TestCase):
    def test_schedules_future_visit_and_trims_reason(self):
        appointment = AppointmentCreate(
            scheduled_date=date.today() + timedelta(days=7),
            start_time=time(9, 45),
            reason_for_visit="  Annual wellness visit  ",
        )
        self.assertEqual(appointment.reason_for_visit, "Annual wellness visit")
        self.assertEqual(appointment.duration_minutes, 30)
        self.assertEqual(appointment.status, "scheduled")

    def test_past_completed_appointment_is_allowed(self):
        appointment = AppointmentCreate(
            scheduled_date=date.today() - timedelta(days=1),
            start_time=time(14, 0),
            duration_minutes=60,
            reason_for_visit="Follow-up",
            status="completed",
        )
        self.assertEqual(appointment.status, "completed")

    def test_blank_reason_is_rejected(self):
        with self.assertRaises(ValidationError):
            AppointmentCreate(
                scheduled_date=date.today(),
                start_time=time(10, 0),
                reason_for_visit="  ",
            )

    def test_duration_is_a_supported_slot(self):
        for duration in (0, 10, 181, 20):
            with self.subTest(duration=duration):
                with self.assertRaises(ValidationError):
                    AppointmentCreate(
                        scheduled_date=date.today(),
                        start_time=time(10, 0),
                        reason_for_visit="Check-up",
                        duration_minutes=duration,
                    )

    def test_invalid_status_is_rejected(self):
        with self.assertRaises(ValidationError):
            AppointmentCreate(
                scheduled_date=date.today(),
                start_time=time(10, 0),
                reason_for_visit="Check-up",
                status="unknown",
            )

    def test_invalid_time_and_overlong_reason_are_rejected(self):
        for fields in (
            {"start_time": "25:90", "reason_for_visit": "Check-up"},
            {"start_time": "10:30", "reason_for_visit": "X" * 201},
        ):
            with self.subTest(fields=fields):
                with self.assertRaises(ValidationError):
                    AppointmentCreate(
                        scheduled_date=date.today(),
                        **fields,
                    )


if __name__ == "__main__":
    unittest.main()
