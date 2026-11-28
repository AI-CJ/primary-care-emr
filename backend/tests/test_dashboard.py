"""Dashboard totals stay private, exact, and consistent with actionable work."""
from datetime import date, datetime, time, timedelta, timezone
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from backend.browser_demo import BROWSER_PASSWORD, create_browser_engine, seed_browser_database
from backend.dashboard import read_work_queue_counts
from backend.main import app
from backend.models import (
    Appointment, AppointmentChangeRequest, CareGoal, Encounter,
    FollowUpTask, LabOrder, LabResult, Patient, Referral,
)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_browser_engine()
        seed_browser_database(self.engine)
        self.addCleanup(self.engine.dispose)
        engine_patch = patch("backend.main.engine", self.engine)
        engine_patch.start()
        self.addCleanup(engine_patch.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.staff = self.login("clinician")

    def login(self, username):
        response = self.client.post("/auth/login", json={
            "username": username, "password": BROWSER_PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def counts(self):
        response = self.client.get("/worklists/counts", headers=self.staff)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_summary_matches_worklists_and_loads_no_clinical_records(self):
        expected = {
            "requests": "appointment-change-requests", "results": "unreleased-lab-results",
            "followups": "open-follow-up-tasks", "labs": "pending-lab-orders",
            "referrals": "pending-referrals", "goals": "active-care-goals",
        }
        counts = self.counts()
        for key, path in expected.items():
            response = self.client.get("/worklists/" + path, headers=self.staff)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(counts[key], len(response.json()), key)

        statements = []
        def record_statement(_connection, _cursor, statement, _parameters, _context, _many):
            statements.append(statement)
        event.listen(self.engine, "before_cursor_execute", record_statement)
        try:
            with Session(self.engine) as session:
                self.assertEqual(read_work_queue_counts(session).model_dump(), counts)
                self.assertEqual(len(session.identity_map), 0)
        finally:
            event.remove(self.engine, "before_cursor_execute", record_statement)
        self.assertEqual(len(statements), 1)
        self.assertTrue(all(type(value) is int for value in counts.values()))

    def test_summary_requires_staff_and_cannot_be_cached(self):
        for headers, status in (({}, 401), (self.login("jordan.lee"), 403),
                                (self.staff, 200), (self.login("admin"), 200)):
            response = self.client.get("/worklists/counts", headers=headers)
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.headers["cache-control"], "no-store")

    def test_archived_charts_are_excluded_and_reactivation_is_current(self):
        original = self.counts()
        self.assertEqual(original, {"requests": 0, "results": 1, "followups": 1,
                                    "labs": 1, "referrals": 1, "goals": 1})
        with Session(self.engine) as session:
            session.get(Patient, 1).archived_at = datetime.now(timezone.utc)
            session.commit()
        self.assertTrue(all(value == 0 for value in self.counts().values()))
        with Session(self.engine) as session:
            session.get(Patient, 1).archived_at = None
            session.commit()
        self.assertEqual(self.counts(), original)

    def test_terminal_states_and_unfinalized_results_are_excluded(self):
        with Session(self.engine) as session:
            session.scalar(select(Encounter)).finalized_at = None
            session.commit()
        self.assertEqual(self.counts()["results"], 0)
        with Session(self.engine) as session:
            session.scalar(select(Encounter)).finalized_at = datetime.now(timezone.utc)
            for result in session.scalars(select(LabResult)):
                result.released_at = datetime.now(timezone.utc)
            for order in session.scalars(select(LabOrder).where(LabOrder.status == "ordered")):
                order.status = "cancelled"
            session.scalar(select(CareGoal)).status = "completed"
            session.scalar(select(FollowUpTask)).status = "cancelled"
            session.scalar(select(Referral)).status = "completed"
            session.commit()
        self.assertTrue(all(value == 0 for value in self.counts().values()))

    def test_request_total_is_exact_beyond_the_worklist_page(self):
        with Session(self.engine) as session:
            appointments = [Appointment(patient_id=1,
                scheduled_date=date.today() + timedelta(days=i + 1),
                start_time=time(9), duration_minutes=30,
                reason_for_visit="Synthetic appointment", status="scheduled")
                for i in range(103)]
            session.add_all(appointments)
            session.flush()
            session.add_all(AppointmentChangeRequest(
                appointment_id=appointment.id, patient_id=1, kind="reschedule",
                status="reviewed" if index == 102 else "pending",
            ) for index, appointment in enumerate(appointments))
            session.commit()
        self.assertEqual(self.counts()["requests"], 102)
        page = self.client.get("/worklists/appointment-change-requests", headers=self.staff)
        self.assertEqual(len(page.json()), 100)
        with Session(self.engine) as session:
            request = session.scalar(select(AppointmentChangeRequest)
                                     .where(AppointmentChangeRequest.status == "pending"))
            request.status = "reviewed"
            session.commit()
        self.assertEqual(self.counts()["requests"], 101)


if __name__ == "__main__":
    unittest.main()
