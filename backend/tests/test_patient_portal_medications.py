"""Authenticated patient access to medication summaries."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import Base, Medication, Patient, UserAccount, UserSession


class PatientPortalMedicationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
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
            self.patient_id, self.other_id, self.empty_id = [p.id for p in patients]
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
                    patient_id=self.other_id, name="Other patient's private medication",
                    status="active", instructions="Other patient's directions",
                ),
            ])
            for username, patient_id in (
                ("avery.portal", self.patient_id),
                ("morgan.portal", self.other_id),
                ("taylor.portal", self.empty_id),
            ):
                create_user_account(
                    session, username=username, password="Fictional portal password!",
                    account_type="patient", patient_id=patient_id,
                )
            create_user_account(
                session, username="clinic.staff", password="Fictional staff password!",
                account_type="staff", staff_role="clinician",
            )
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def login(self, client, username, password="Fictional portal password!"):
        response = client.post("/auth/login", json={
            "username": username, "password": password,
        })
        self.assertEqual(response.status_code, 200)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_patient_gets_only_own_medications_and_display_fields(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            morgan = self.login(client, "morgan.portal")
            taylor = self.login(client, "taylor.portal")
            response = client.get("/portal/medications", headers=avery)
            other = client.get("/portal/medications", headers=morgan)
            empty = client.get("/portal/medications", headers=taylor)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual([m["name"] for m in response.json()], [
                "Fictional vitamin", "Fictional ointment", "Fictional drops",
            ])
            self.assertEqual([m["status"] for m in response.json()], [
                "active", "completed", "discontinued",
            ])
            self.assertEqual(response.json()[0]["strength"], "100 mg")
            self.assertEqual(response.json()[0]["dose"], "One tablet")
            self.assertEqual(response.json()[0]["frequency"], "Daily")
            self.assertEqual(response.json()[0]["start_date"], "2026-09-01")
            self.assertEqual(response.json()[0]["instructions"], "Take with breakfast")
            self.assertEqual(response.json()[1]["end_date"], "2026-08-01")
            self.assertEqual(response.json()[2]["end_date"], "2026-10-03")
            self.assertEqual(set(response.json()[0]), {
                "id", "name", "strength", "dose", "frequency", "status",
                "start_date", "end_date", "instructions",
            })
            self.assertNotIn("route", response.json()[0])
            self.assertNotIn("patient_id", response.text)
            self.assertNotIn("Other patient's", response.text)
            self.assertEqual([m["name"] for m in other.json()],
                             ["Other patient's private medication"])
            self.assertEqual(empty.json(), [])

            overridden = client.get(
                f"/portal/medications?patient_id={self.other_id}", headers=avery,
            )
            self.assertEqual(overridden.status_code, 200)
            self.assertEqual(overridden.json(), response.json())

    def test_endpoint_is_patient_only_and_cannot_edit_medications(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            response = client.get("/portal/medications")
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["www-authenticate"], "Bearer")
            self.assertEqual(client.get("/portal/medications", headers={
                "Authorization": "Bearer invalid-token",
            }).status_code, 401)

            staff = self.login(client, "clinic.staff", "Fictional staff password!")
            self.assertEqual(client.get("/portal/medications", headers=staff).status_code, 403)
            self.assertEqual(client.get(
                f"/patients/{self.other_id}/portal-preview/medications",
                headers=staff,
            ).status_code, 200)

            avery = self.login(client, "avery.portal")
            for path in (
                "/patients",
                f"/patients/{self.other_id}/medications",
                f"/patients/{self.other_id}/portal-preview/medications",
                "/portal/medications/1",
            ):
                with self.subTest(path=path):
                    self.assertEqual(client.get(path, headers=avery).status_code, 403)
            self.assertEqual(client.post(
                "/portal/medications", json={"name": "Fake refill"}, headers=avery,
            ).status_code, 403)

    def test_revoked_expired_and_disabled_sessions(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            self.assertEqual(client.get("/portal/medications", headers=avery).status_code, 200)
            self.assertEqual(client.post("/auth/logout", headers=avery).status_code, 204)
            self.assertEqual(client.get("/portal/medications", headers=avery).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                record = session.query(UserSession).filter_by(revoked_at=None).one()
                record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                session.commit()
            self.assertEqual(client.get("/portal/medications", headers=avery).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                session.query(UserAccount).filter_by(
                    username="avery.portal",
                ).one().is_active = False
                session.commit()
            self.assertEqual(client.get("/portal/medications", headers=avery).status_code, 401)


if __name__ == "__main__":
    unittest.main()
