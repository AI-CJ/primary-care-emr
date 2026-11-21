"""Verify patient-specific access to finalized visit summaries."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import Base, Encounter, Patient, UserAccount, UserSession


class PatientPortalVisitTests(unittest.TestCase):
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
                    first_name=name,
                    last_name="Example",
                    date_of_birth=date(1990, 6, 12),
                    sex_at_birth="unknown",
                )
                for name in ("Avery", "Morgan", "Taylor")
            ]
            session.add_all(patients)
            session.flush()
            self.patient_id, self.other_id, self.empty_id = [p.id for p in patients]
            finalized = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)

            for day in range(1, 8):
                session.add(Encounter(
                    patient_id=self.patient_id,
                    visit_date=date(2026, 10, day),
                    reason_for_visit=f"Fictional visit {day}",
                    subjective="Private patient history",
                    assessment="Private clinical assessment",
                    plan="Private clinical plan",
                    patient_instructions=(
                        "Bring fictional readings next time" if day == 7 else None
                    ),
                    finalized_at=finalized,
                ))

            session.add_all([
                Encounter(
                    patient_id=self.patient_id,
                    visit_date=date(2026, 11, 8),
                    reason_for_visit="Unfinalized patient note",
                    subjective="Draft-only patient history",
                    patient_instructions="Draft-only instructions",
                ),
                Encounter(
                    patient_id=self.other_id,
                    visit_date=date(2026, 11, 9),
                    reason_for_visit="Another patient's visit",
                    patient_instructions="Another patient's instructions",
                    finalized_at=finalized,
                ),
            ])
            for username, patient_id in (
                ("avery.portal", self.patient_id),
                ("morgan.portal", self.other_id),
                ("taylor.portal", self.empty_id),
            ):
                create_user_account(
                    session, username=username,
                    password="Fictional portal password!",
                    account_type="patient", patient_id=patient_id,
                )
            create_user_account(
                session, username="clinic.staff",
                password="Fictional staff password!",
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

    def test_only_own_recent_finalized_visits_and_safe_fields(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            morgan = self.login(client, "morgan.portal")
            taylor = self.login(client, "taylor.portal")

            response = client.get("/portal/visits", headers=avery)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(
                [visit["reason_for_visit"] for visit in response.json()],
                [f"Fictional visit {day}" for day in (7, 6, 5, 4, 3)],
            )
            self.assertEqual(
                response.json()[0]["patient_instructions"],
                "Bring fictional readings next time",
            )
            self.assertEqual(response.json()[1]["patient_instructions"], None)
            self.assertEqual(set(response.json()[0]), {
                "id", "visit_date", "reason_for_visit", "patient_instructions",
            })
            for private in (
                "patient_id", "subjective", "objective", "assessment", "plan",
                "Private patient history", "Private clinical assessment",
                "Private clinical plan", "Draft-only", "Another patient's",
            ):
                self.assertNotIn(private, response.text)

            self.assertEqual(
                [visit["reason_for_visit"] for visit in client.get(
                    "/portal/visits", headers=morgan,
                ).json()],
                ["Another patient's visit"],
            )
            self.assertEqual(client.get("/portal/visits", headers=taylor).json(), [])

            override = client.get(
                f"/portal/visits?patient_id={self.other_id}", headers=avery,
            )
            self.assertEqual(override.status_code, 200)
            self.assertEqual(override.json(), response.json())

    def test_patient_access_is_read_only_and_staff_is_separate(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            missing = client.get("/portal/visits")
            self.assertEqual(missing.status_code, 401)
            self.assertEqual(missing.headers["www-authenticate"], "Bearer")
            self.assertEqual(client.get(
                "/portal/visits", headers={"Authorization": "Bearer invalid"},
            ).status_code, 401)

            staff = self.login(client, "clinic.staff", "Fictional staff password!")
            self.assertEqual(client.get("/portal/visits", headers=staff).status_code, 403)
            self.assertEqual(client.get(
                f"/patients/{self.patient_id}/portal-preview/visits",
                headers=staff,
            ).status_code, 200)

            avery = self.login(client, "avery.portal")
            for path in (
                "/patients",
                f"/patients/{self.other_id}/portal-preview/visits",
                f"/patients/{self.other_id}/encounters",
                "/portal/visits/1",
            ):
                with self.subTest(path=path):
                    self.assertEqual(client.get(path, headers=avery).status_code, 403)
            self.assertEqual(client.post(
                "/portal/visits", headers=avery,
                json={"reason_for_visit": "Not allowed"},
            ).status_code, 403)

    def test_revoked_expired_and_disabled_sessions(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            self.assertEqual(client.get("/portal/visits", headers=avery).status_code, 200)
            self.assertEqual(client.post("/auth/logout", headers=avery).status_code, 204)
            self.assertEqual(client.get("/portal/visits", headers=avery).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                record = session.query(UserSession).filter_by(revoked_at=None).one()
                record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                session.commit()
            self.assertEqual(client.get("/portal/visits", headers=avery).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                session.query(UserAccount).filter_by(
                    username="avery.portal",
                ).one().is_active = False
                session.commit()
            self.assertEqual(client.get("/portal/visits", headers=avery).status_code, 401)


if __name__ == "__main__":
    unittest.main()
