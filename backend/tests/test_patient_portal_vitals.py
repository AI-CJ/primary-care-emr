"""Patient-scoped access to recent vital measurements."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import Base, Patient, UserAccount, UserSession, Vital


class PatientPortalVitalTests(unittest.TestCase):
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
                Vital(
                    patient_id=self.patient_id, recorded_on=date(2026, 9, 1),
                    heart_rate=66, notes="Older clinical note",
                ),
                Vital(
                    patient_id=self.patient_id, recorded_on=date(2026, 10, 1),
                    systolic_bp=120, diastolic_bp=80, notes="Private assessment",
                ),
                Vital(
                    patient_id=self.patient_id, recorded_on=date(2026, 11, 1),
                    oxygen_saturation=98, notes="Staff-only observation",
                ),
                Vital(
                    patient_id=self.patient_id, recorded_on=date(2026, 11, 1),
                    height_cm=180.0, weight_kg=82.5,
                ),
                Vital(
                    patient_id=self.other_id, recorded_on=date(2026, 11, 2),
                    heart_rate=99, notes="Another patient's private note",
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

    def test_only_own_three_most_recent_measurements_and_public_fields(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            morgan = self.login(client, "morgan.portal")
            taylor = self.login(client, "taylor.portal")

            response = client.get("/portal/vitals", headers=avery)
            other = client.get("/portal/vitals", headers=morgan)
            empty = client.get("/portal/vitals", headers=taylor)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            vitals = response.json()
            self.assertEqual(len(vitals), 3)
            self.assertEqual(
                [vital["recorded_on"] for vital in vitals],
                ["2026-11-01", "2026-11-01", "2026-10-01"],
            )
            self.assertEqual(vitals[0]["weight_kg"], 82.5)
            self.assertEqual(vitals[0]["height_cm"], 180.0)
            self.assertEqual(vitals[1]["oxygen_saturation"], 98)
            self.assertEqual(vitals[2]["systolic_bp"], 120)
            self.assertEqual(set(vitals[0]), {
                "id", "recorded_on", "systolic_bp", "diastolic_bp",
                "heart_rate", "respiratory_rate", "temperature_c",
                "oxygen_saturation", "height_cm", "weight_kg",
            })
            for secret in (
                "notes", "patient_id", "Older clinical note", "Private assessment",
                "Staff-only observation", "Another patient's",
            ):
                self.assertNotIn(secret, response.text)
            self.assertEqual(len(other.json()), 1)
            self.assertEqual(other.json()[0]["heart_rate"], 99)
            self.assertEqual(empty.json(), [])

            # A query parameter cannot choose another patient's chart.
            override = client.get(
                f"/portal/vitals?patient_id={self.other_id}", headers=avery,
            )
            self.assertEqual(override.status_code, 200)
            self.assertEqual(override.json(), vitals)

    def test_patient_only_and_read_only(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            missing = client.get("/portal/vitals")
            self.assertEqual(missing.status_code, 401)
            self.assertEqual(missing.headers["www-authenticate"], "Bearer")
            self.assertEqual(client.get("/portal/vitals", headers={
                "Authorization": "Bearer bogus-token",
            }).status_code, 401)

            staff = self.login(client, "clinic.staff", "Fictional staff password!")
            self.assertEqual(client.get("/portal/vitals", headers=staff).status_code, 403)
            self.assertEqual(client.get(
                f"/patients/{self.other_id}/portal-preview/vitals",
                headers=staff,
            ).status_code, 200)

            avery = self.login(client, "avery.portal")
            for path in (
                "/patients",
                f"/patients/{self.other_id}/vitals",
                f"/patients/{self.other_id}/portal-preview/vitals",
                "/portal/vitals/1",
            ):
                with self.subTest(path=path):
                    self.assertEqual(client.get(path, headers=avery).status_code, 403)
            self.assertEqual(client.post(
                "/portal/vitals",
                json={"recorded_on": "2026-11-01", "heart_rate": 72},
                headers=avery,
            ).status_code, 403)

    def test_revoked_expired_and_disabled_sessions(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            self.assertEqual(client.get("/portal/vitals", headers=avery).status_code, 200)
            self.assertEqual(client.post("/auth/logout", headers=avery).status_code, 204)
            self.assertEqual(client.get("/portal/vitals", headers=avery).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                record = session.query(UserSession).filter_by(revoked_at=None).one()
                record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                session.commit()
            self.assertEqual(client.get("/portal/vitals", headers=avery).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                session.query(UserAccount).filter_by(
                    username="avery.portal",
                ).one().is_active = False
                session.commit()
            self.assertEqual(client.get("/portal/vitals", headers=avery).status_code, 401)


if __name__ == "__main__":
    unittest.main()
