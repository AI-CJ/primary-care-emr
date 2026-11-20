"""Authentication HTTP endpoints with fictional accounts."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import Base, Patient, UserAccount, UserSession


class AuthRoutesTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Alex", last_name="Sample",
                date_of_birth=date(1993, 3, 12), sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            self.patient_id = patient.id
            create_user_account(
                session, username="sample.staff",
                password="Synthetic staff password!",
                account_type="staff", staff_role="clinician",
            )
            create_user_account(
                session, username="sample.patient",
                password="Synthetic patient password!",
                account_type="patient", patient_id=patient.id,
            )
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_login_me_and_logout(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            response = client.post("/auth/login", json={
                "username": "SAMPLE.STAFF", "password": "Synthetic staff password!",
            })
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["token_type"], "bearer")
            self.assertIn("expires_at", data)
            token = data["access_token"]
            header = {"Authorization": f"Bearer {token}"}
            me = client.get("/auth/me", headers=header)
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.json()["username"], "sample.staff")
            self.assertEqual(me.json()["staff_role"], "clinician")
            self.assertIsNone(me.json()["patient_id"])
            self.assertNotIn("password_hash", me.json())
            self.assertNotIn("access_token", me.json())
            self.assertEqual(client.post("/auth/logout", headers=header).status_code, 204)
            self.assertEqual(client.get("/auth/me", headers=header).status_code, 401)
            self.assertEqual(client.post("/auth/logout", headers=header).status_code, 401)

    def test_patient_scope_is_only_that_patient(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            response = client.post("/auth/login", json={
                "username": "sample.patient", "password": "Synthetic patient password!",
            })
            self.assertEqual(response.status_code, 200)
            me = client.get("/auth/me", headers={
                "Authorization": f"Bearer {response.json()['access_token']}",
            })
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.json()["account_type"], "patient")
            self.assertEqual(me.json()["patient_id"], self.patient_id)
            self.assertIsNone(me.json()["staff_role"])

    def test_invalid_credentials_and_missing_bearer(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            for username, password in (
                ("sample.staff", "Wrong password"),
                ("missing.staff", "Synthetic staff password!"),
                ("not valid", "Synthetic staff password!"),
            ):
                with self.subTest(username=username):
                    response = client.post("/auth/login", json={
                        "username": username, "password": password,
                    })
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.json()["detail"], "Invalid or missing credentials")
            self.assertEqual(client.post("/auth/login", json={
                "username": "sample.staff", "password": "",
            }).status_code, 422)
            self.assertEqual(client.get("/auth/me").status_code, 401)
            self.assertEqual(client.get("/auth/me", headers={
                "Authorization": "Bearer invalid",
            }).status_code, 401)

    def test_expired_token_and_disabled_account(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            response = client.post("/auth/login", json={
                "username": "sample.staff", "password": "Synthetic staff password!",
            })
            token = response.json()["access_token"]
            header = {"Authorization": f"Bearer {token}"}
            with Session(self.engine) as session:
                record = session.query(UserSession).one()
                record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                session.commit()
            self.assertEqual(client.get("/auth/me", headers=header).status_code, 401)
            with Session(self.engine) as session:
                session.query(UserSession).one().expires_at = (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                )
                session.query(UserAccount).filter_by(username="sample.staff").one().is_active = False
                session.commit()
            self.assertEqual(client.get("/auth/me", headers=header).status_code, 401)
            self.assertEqual(client.post("/auth/login", json={
                "username": "sample.staff", "password": "Synthetic staff password!",
            }).status_code, 401)


if __name__ == "__main__":
    unittest.main()
