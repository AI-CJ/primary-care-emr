"""Read-only clinic schedule using synthetic patients and appointments."""

import unittest
from datetime import date, time, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Appointment, Base, Patient
from backend.schemas import AppointmentRead, ScheduleEntryRead, SchedulePatientRead
from backend.scheduling import list_daily_schedule


class DailyScheduleTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.day = date(2026, 11, 12)
        with Session(self.engine) as session:
            first = Patient(
                first_name="Casey",
                preferred_name="Caz",
                last_name="Example",
                date_of_birth=date(1989, 6, 5),
                sex_at_birth="unknown",
            )
            second = Patient(
                first_name="Jordan",
                last_name="Carter",
                date_of_birth=date(1991, 2, 20),
                sex_at_birth="unknown",
            )
            session.add_all([first, second])
            session.flush()
            self.first_id, self.second_id = first.id, second.id
            session.add_all([
                self.appointment(self.first_id, time(11), "cancelled"),
                self.appointment(self.first_id, time(9), "no_show"),
                self.appointment(self.second_id, time(9), "scheduled"),
                self.appointment(self.first_id, time(8), "checked_in"),
                self.appointment(
                    self.second_id,
                    time(7),
                    "completed",
                    day=self.day + timedelta(days=1),
                ),
            ])
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def appointment(self, patient_id, at, status, *, day=None):
        return Appointment(
            patient_id=patient_id,
            scheduled_date=day or self.day,
            start_time=at,
            duration_minutes=30,
            reason_for_visit="Fictional office visit",
            status=status,
        )

    def test_filters_by_date_and_orders_by_time_then_last_name(self):
        with Session(self.engine) as session:
            rows = list_daily_schedule(session, self.day)
            self.assertEqual(
                [(a.start_time, p.last_name) for a, p in rows],
                [
                    (time(8), "Example"),
                    (time(9), "Carter"),
                    (time(9), "Example"),
                    (time(11), "Example"),
                ],
            )
            self.assertEqual(
                [a.status for a, _ in rows],
                ["checked_in", "scheduled", "no_show", "cancelled"],
            )

    def test_schedule_entry_includes_minimal_patient_summary(self):
        with Session(self.engine) as session:
            appointment, patient = list_daily_schedule(session, self.day)[0]
            entry = ScheduleEntryRead(
                appointment=AppointmentRead.model_validate(appointment),
                patient=SchedulePatientRead.model_validate(patient),
            )
            data = entry.model_dump(mode="json")
            self.assertEqual(data["patient"]["preferred_name"], "Caz")
            self.assertEqual(data["patient"]["date_of_birth"], "1989-06-05")
            self.assertEqual(data["appointment"]["patient_id"], self.first_id)
            self.assertNotIn("sex_at_birth", data["patient"])

    def test_no_appointments_returns_empty_list(self):
        with Session(self.engine) as session:
            self.assertEqual(
                list_daily_schedule(session, date(2026, 11, 20)), []
            )


if __name__ == "__main__":
    unittest.main()
