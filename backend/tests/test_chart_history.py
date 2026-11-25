"""Access-control and lifecycle regression tests for historical chart context."""
from datetime import date, timedelta
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.browser_demo import BROWSER_PASSWORD, create_browser_engine, seed_browser_database
from backend.main import app
from backend.models import ImagingReport, PatientBackground


class ChartHistoryAccessTests(TestCase):
    def setUp(self):
        self.engine = create_browser_engine()
        seed_browser_database(self.engine)
        self.addCleanup(self.engine.dispose)
        today = date.today()
        with Session(self.engine) as session:
            session.add(PatientBackground(
                patient_id=1, reviewed_on=today, medical_history="Previously reviewed history.",
                surgical_history="No operations reported.", family_history="Family history incomplete.",
                social_history="Lives independently.", care_context="Prefers written instructions.",
            ))
            for patient_id, study, shared in (
                (1, "Shared knee report", today - timedelta(days=2)),
                (1, "Unshared knee report", None),
                (1, "Future shared report", today + timedelta(days=2)),
                (2, "Other patient report", today - timedelta(days=2)),
            ):
                session.add(ImagingReport(
                    patient_id=patient_id, performed_on=today - timedelta(days=10),
                    reported_on=today - timedelta(days=9), modality="Radiograph",
                    study=study, indication="Historical evaluation", findings="Recorded findings",
                    impression="Recorded impression", source="Prior report", shared_on=shared,
                ))
            session.commit()
        engine_patch = patch("backend.main.engine", self.engine)
        engine_patch.start()
        self.addCleanup(engine_patch.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.staff = self.login("admin")
        self.jordan = self.login("jordan.lee")
        self.maria = self.login("maria.thompson")

    def login(self, username):
        response = self.client.post("/auth/login", json={"username": username, "password": BROWSER_PASSWORD})
        self.assertEqual(response.status_code, 200)
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def read(self, path, headers, expected=200):
        response = self.client.get(path, headers=headers)
        self.assertEqual(response.status_code, expected, response.text)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        return response.json()

    def test_background_staff_only_and_missing_state(self):
        path = "/patients/1/background"
        self.read(path, {}, 401)
        self.read(path, self.jordan, 403)
        self.assertEqual(self.read(path, self.staff)["patient_id"], 1)
        self.assertIsNone(self.read("/patients/2/background", self.staff))
        self.read("/patients/99999/background", self.staff, 404)

    def test_report_visibility_and_portal_ownership(self):
        path = "/patients/1/imaging-reports"
        self.read(path, {}, 401)
        self.read(path, self.jordan, 403)
        self.read("/patients/2/portal-preview/imaging-reports", self.jordan, 403)
        records = self.read(path, self.staff)
        self.assertEqual({row["study"] for row in records},
                         {"Shared knee report", "Unshared knee report", "Future shared report"})
        preview = self.read("/patients/1/portal-preview/imaging-reports", self.staff)
        jordan = self.read("/portal/imaging-reports", self.jordan)
        maria = self.read("/portal/imaging-reports", self.maria)
        self.assertEqual(preview, jordan)
        self.assertEqual([row["study"] for row in jordan], ["Shared knee report"])
        self.assertEqual([row["study"] for row in maria], ["Other patient report"])
        self.assertNotIn("patient_id", jordan[0])
        self.assertNotIn("shared_on", jordan[0])
        self.read("/portal/imaging-reports", self.staff, 403)
        self.read("/portal/imaging-reports", {}, 401)
