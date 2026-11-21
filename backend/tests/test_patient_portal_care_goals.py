"""Check that patients can only read their own care goal summaries."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import Base, CareGoal, Patient, UserAccount, UserSession


class PatientPortalCareGoalTests(unittest.TestCase):
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
                CareGoal(
                    patient_id=self.patient_id, title="Walk after lunch",
                    status="active", target_date=date(2027, 1, 15),
                    created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                ),
                CareGoal(
                    patient_id=self.patient_id, title="Track daily walks",
                    status="completed", completion_note="Private clinical assessment",
                    completed_at=datetime(2026, 11, 3, tzinfo=timezone.utc),
                    created_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
                ),
                CareGoal(
                    patient_id=self.patient_id, title="Old exercise target",
                    status="discontinued", discontinuation_reason="Staff-only rationale",
                    discontinued_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
                    created_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
                ),
                CareGoal(
                    patient_id=self.other_id, title="Another patient's private goal",
                    status="active",
                    created_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
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

    def test_patient_scope_status_history_and_public_fields(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            morgan = self.login(client, "morgan.portal")
            taylor = self.login(client, "taylor.portal")

            response = client.get("/portal/care-goals", headers=avery)
            other = client.get("/portal/care-goals", headers=morgan)
            empty = client.get("/portal/care-goals", headers=taylor)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(
                [goal["title"] for goal in response.json()],
                ["Old exercise target", "Track daily walks", "Walk after lunch"],
            )
            self.assertEqual(
                [goal["status"] for goal in response.json()],
                ["discontinued", "completed", "active"],
            )
            self.assertEqual(response.json()[0]["discontinued_at"][:10], "2026-11-04")
            self.assertEqual(response.json()[1]["completed_at"][:10], "2026-11-03")
            self.assertEqual(response.json()[2]["target_date"], "2027-01-15")
            self.assertEqual(set(response.json()[0]), {
                "id", "title", "target_date", "status", "created_at",
                "completed_at", "discontinued_at",
            })
            for secret in (
                "patient_id", "completion_note", "discontinuation_reason",
                "Private clinical assessment", "Staff-only rationale",
                "Another patient's private goal",
            ):
                self.assertNotIn(secret, response.text)
            self.assertEqual([goal["title"] for goal in other.json()],
                             ["Another patient's private goal"])
            self.assertEqual(empty.json(), [])

            override = client.get(
                f"/portal/care-goals?patient_id={self.other_id}", headers=avery,
            )
            self.assertEqual(override.status_code, 200)
            self.assertEqual(override.json(), response.json())

    def test_requires_patient_session_and_does_not_grant_clinical_access(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            missing = client.get("/portal/care-goals")
            self.assertEqual(missing.status_code, 401)
            self.assertEqual(missing.headers["www-authenticate"], "Bearer")
            self.assertEqual(client.get("/portal/care-goals", headers={
                "Authorization": "Bearer invalid",
            }).status_code, 401)

            staff = self.login(client, "clinic.staff", "Fictional staff password!")
            self.assertEqual(client.get("/portal/care-goals", headers=staff).status_code, 403)
            self.assertEqual(client.get(
                f"/patients/{self.other_id}/portal-preview/care-goals",
                headers=staff,
            ).status_code, 200)

            avery = self.login(client, "avery.portal")
            for path in (
                "/patients",
                f"/patients/{self.other_id}/care-goals",
                f"/patients/{self.other_id}/portal-preview/care-goals",
                "/care-goals/1/progress",
                "/portal/care-goals/1",
            ):
                with self.subTest(path=path):
                    self.assertEqual(client.get(path, headers=avery).status_code, 403)
            self.assertEqual(client.post(
                "/portal/care-goals",
                json={"title": "Unauthorized goal"},
                headers=avery,
            ).status_code, 403)

    def test_revoked_expired_and_disabled_sessions(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            self.assertEqual(client.get("/portal/care-goals", headers=avery).status_code, 200)
            self.assertEqual(client.post("/auth/logout", headers=avery).status_code, 204)
            self.assertEqual(client.get("/portal/care-goals", headers=avery).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                record = session.query(UserSession).filter_by(revoked_at=None).one()
                record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                session.commit()
            self.assertEqual(client.get("/portal/care-goals", headers=avery).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                session.query(UserAccount).filter_by(
                    username="avery.portal",
                ).one().is_active = False
                session.commit()
            self.assertEqual(client.get("/portal/care-goals", headers=avery).status_code, 401)


if __name__ == "__main__":
    unittest.main()
