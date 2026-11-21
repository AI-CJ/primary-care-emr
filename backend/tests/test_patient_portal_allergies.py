"""Authenticated patients can read only their own allergy summaries."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import Allergy, Base, Patient, UserAccount, UserSession


class PatientPortalAllergyTests(unittest.TestCase):
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
                    first_name=name, last_name="Example",
                    date_of_birth=date(1990, 6, 12), sex_at_birth="unknown",
                )
                for name in ("Avery", "Morgan", "Taylor")
            ]
            session.add_all(patients)
            session.flush()
            self.patient_id, self.other_id, self.empty_id = [p.id for p in patients]
            session.add_all([
                Allergy(
                    patient_id=self.patient_id, allergen="Fictional adhesive",
                    severity="severe", status="active", reaction="Rash",
                    notes="Staff-only allergy notes",
                ),
                Allergy(
                    patient_id=self.patient_id, allergen="Fictional pollen",
                    severity="mild", status="active", reaction="Sneezing",
                    onset_date=date(2025, 4, 3),
                ),
                Allergy(
                    patient_id=self.patient_id, allergen="Fictional tablet",
                    severity="unknown", status="inactive",
                    onset_date=date(2024, 9, 8), notes="Private reassessment",
                ),
                Allergy(
                    patient_id=self.other_id, allergen="Other patient's allergen",
                    severity="unknown", status="active", notes="Other patient's private notes",
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

    def test_patient_gets_only_own_allergies_and_limited_fields(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            morgan = self.login(client, "morgan.portal")
            taylor = self.login(client, "taylor.portal")

            response = client.get("/portal/allergies", headers=avery)
            other = client.get("/portal/allergies", headers=morgan)
            empty = client.get("/portal/allergies", headers=taylor)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual([item["allergen"] for item in response.json()], [
                "Fictional adhesive", "Fictional pollen", "Fictional tablet",
            ])
            self.assertEqual([item["status"] for item in response.json()], [
                "active", "active", "inactive",
            ])
            self.assertEqual(response.json()[0]["reaction"], "Rash")
            self.assertEqual(response.json()[0]["severity"], "severe")
            self.assertEqual(response.json()[1]["onset_date"], "2025-04-03")
            self.assertEqual(response.json()[2]["onset_date"], "2024-09-08")
            self.assertEqual(set(response.json()[0]), {
                "id", "allergen", "reaction", "severity", "status", "onset_date",
            })
            self.assertNotIn("notes", response.text)
            self.assertNotIn("patient_id", response.text)
            self.assertNotIn("Staff-only", response.text)
            self.assertNotIn("Private reassessment", response.text)
            self.assertNotIn("Other patient's", response.text)
            self.assertEqual([item["allergen"] for item in other.json()],
                             ["Other patient's allergen"])
            self.assertEqual(empty.json(), [])

            # A query string must not override the account-bound patient ID.
            overridden = client.get(
                f"/portal/allergies?patient_id={self.other_id}", headers=avery,
            )
            self.assertEqual(overridden.status_code, 200)
            self.assertEqual(overridden.json(), response.json())

    def test_patient_endpoint_is_read_only_and_not_for_staff(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            missing = client.get("/portal/allergies")
            self.assertEqual(missing.status_code, 401)
            self.assertEqual(missing.headers["www-authenticate"], "Bearer")
            self.assertEqual(client.get("/portal/allergies", headers={
                "Authorization": "Bearer invalid-token",
            }).status_code, 401)

            staff = self.login(client, "clinic.staff", "Fictional staff password!")
            self.assertEqual(client.get("/portal/allergies", headers=staff).status_code, 403)
            self.assertEqual(client.get(
                f"/patients/{self.other_id}/portal-preview/allergies",
                headers=staff,
            ).status_code, 200)

            avery = self.login(client, "avery.portal")
            for path in (
                "/patients",
                f"/patients/{self.other_id}/allergies",
                f"/patients/{self.other_id}/portal-preview/allergies",
                "/portal/allergies/1",
            ):
                with self.subTest(path=path):
                    self.assertEqual(client.get(path, headers=avery).status_code, 403)
            self.assertEqual(client.post(
                "/portal/allergies", json={"allergen": "Fake entry"}, headers=avery,
            ).status_code, 403)

    def test_revoked_expired_and_disabled_sessions(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            self.assertEqual(client.get("/portal/allergies", headers=avery).status_code, 200)
            self.assertEqual(client.post("/auth/logout", headers=avery).status_code, 204)
            self.assertEqual(client.get("/portal/allergies", headers=avery).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                record = session.query(UserSession).filter_by(revoked_at=None).one()
                record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                session.commit()
            self.assertEqual(client.get("/portal/allergies", headers=avery).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                session.query(UserAccount).filter_by(
                    username="avery.portal",
                ).one().is_active = False
                session.commit()
            self.assertEqual(client.get("/portal/allergies", headers=avery).status_code, 401)


if __name__ == "__main__":
    unittest.main()
