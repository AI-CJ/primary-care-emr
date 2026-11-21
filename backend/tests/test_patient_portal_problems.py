"""Authenticated patient access to their own problem summary."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import Base, Patient, Problem, UserAccount, UserSession


class PatientPortalProblemTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            first = Patient(
                first_name="Robin", last_name="Example",
                date_of_birth=date(1990, 1, 2), sex_at_birth="unknown",
            )
            second = Patient(
                first_name="Casey", last_name="Example",
                date_of_birth=date(1991, 3, 4), sex_at_birth="unknown",
            )
            empty = Patient(
                first_name="Lee", last_name="Example",
                date_of_birth=date(1992, 5, 6), sex_at_birth="unknown",
            )
            session.add_all([first, second, empty])
            session.flush()
            self.first_id = first.id
            self.second_id = second.id
            session.add_all([
                Problem(
                    patient_id=first.id, name="Synthetic asthma", status="active",
                    onset_date=date(2026, 1, 10), notes="Staff-only private notes",
                ),
                Problem(
                    patient_id=first.id, name="Synthetic sprain", status="resolved",
                    resolved_date=date(2026, 10, 1), notes="Private clinical history",
                ),
                Problem(
                    patient_id=second.id, name="Casey's confidential condition",
                    status="active", notes="Another patient's private notes",
                ),
            ])
            create_user_account(
                session, username="robin.portal", password="Fictional Robin password!",
                account_type="patient", patient_id=first.id,
            )
            create_user_account(
                session, username="casey.portal", password="Fictional Casey password!",
                account_type="patient", patient_id=second.id,
            )
            create_user_account(
                session, username="lee.portal", password="Fictional Lee password!",
                account_type="patient", patient_id=empty.id,
            )
            create_user_account(
                session, username="clinic.staff", password="Fictional staff password!",
                account_type="staff", staff_role="clinician",
            )
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def login(self, client, username, password):
        response = client.post("/auth/login", json={
            "username": username, "password": password,
        })
        self.assertEqual(response.status_code, 200)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_patients_receive_only_their_own_display_fields(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            robin = self.login(client, "robin.portal", "Fictional Robin password!")
            casey = self.login(client, "casey.portal", "Fictional Casey password!")
            lee = self.login(client, "lee.portal", "Fictional Lee password!")
            first = client.get("/portal/problems", headers=robin)
            second = client.get("/portal/problems", headers=casey)
            empty = client.get("/portal/problems", headers=lee)

            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(empty.status_code, 200)
            self.assertEqual(first.headers["cache-control"], "no-store")
            self.assertEqual([p["name"] for p in first.json()],
                             ["Synthetic asthma", "Synthetic sprain"])
            self.assertEqual([p["status"] for p in first.json()],
                             ["active", "resolved"])
            self.assertEqual(first.json()[0]["onset_date"], "2026-01-10")
            self.assertEqual(first.json()[1]["resolved_date"], "2026-10-01")
            self.assertEqual([p["name"] for p in second.json()],
                             ["Casey's confidential condition"])
            self.assertEqual(empty.json(), [])
            self.assertEqual(
                set(first.json()[0]),
                {"id", "name", "status", "onset_date", "resolved_date"},
            )
            self.assertNotIn("patient_id", first.text)
            self.assertNotIn("notes", first.text)
            self.assertNotIn("Staff-only", first.text)
            self.assertNotIn("Casey's confidential", first.text)

            override = client.get(
                f"/portal/problems?patient_id={self.second_id}", headers=robin,
            )
            self.assertEqual(override.status_code, 200)
            self.assertEqual(override.json(), first.json())

    def test_patient_route_requires_patient_session_and_stays_read_only(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            missing = client.get("/portal/problems")
            self.assertEqual(missing.status_code, 401)
            self.assertEqual(missing.headers["www-authenticate"], "Bearer")
            self.assertEqual(client.get("/portal/problems", headers={
                "Authorization": "Bearer not-a-session",
            }).status_code, 401)

            staff = self.login(client, "clinic.staff", "Fictional staff password!")
            self.assertEqual(client.get("/portal/problems", headers=staff).status_code, 403)
            self.assertEqual(
                client.get(f"/patients/{self.second_id}/portal-preview/problems",
                           headers=staff).status_code, 200,
            )

            robin = self.login(client, "robin.portal", "Fictional Robin password!")
            for path in (
                "/patients",
                f"/patients/{self.second_id}/portal-preview/problems",
                "/portal/problems/1",
            ):
                with self.subTest(path=path):
                    self.assertEqual(client.get(path, headers=robin).status_code, 403)
            self.assertEqual(
                client.post("/portal/problems", headers=robin).status_code, 403
            )

    def test_revoked_expired_and_disabled_patient_sessions(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            robin = self.login(client, "robin.portal", "Fictional Robin password!")
            self.assertEqual(client.get("/portal/problems", headers=robin).status_code, 200)
            self.assertEqual(client.post("/auth/logout", headers=robin).status_code, 204)
            self.assertEqual(client.get("/portal/problems", headers=robin).status_code, 401)

            robin = self.login(client, "robin.portal", "Fictional Robin password!")
            with Session(self.engine) as session:
                record = session.query(UserSession).filter_by(revoked_at=None).one()
                record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                session.commit()
            self.assertEqual(client.get("/portal/problems", headers=robin).status_code, 401)

            robin = self.login(client, "robin.portal", "Fictional Robin password!")
            with Session(self.engine) as session:
                session.query(UserAccount).filter_by(
                    username="robin.portal",
                ).one().is_active = False
                session.commit()
            self.assertEqual(client.get("/portal/problems", headers=robin).status_code, 401)


if __name__ == "__main__":
    unittest.main()
