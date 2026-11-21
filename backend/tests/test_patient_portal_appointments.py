"""Only the signed-in patient can retrieve their portal appointments."""

import unittest
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import Appointment, Base, Patient, UserAccount, UserSession


class PatientPortalAppointmentTests(unittest.TestCase):
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
            session.add_all([first, second])
            session.flush()
            self.first_id = first.id
            self.second_id = second.id
            session.add_all([
                Appointment(
                    patient_id=first.id, scheduled_date=date(2026, 11, 18),
                    start_time=time(10, 30), duration_minutes=30,
                    reason_for_visit="Robin's synthetic follow-up",
                    status="completed",
                ),
                Appointment(
                    patient_id=second.id, scheduled_date=date(2026, 11, 19),
                    start_time=time(9, 0), duration_minutes=60,
                    reason_for_visit="Casey's private synthetic appointment",
                    status="scheduled",
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

    def test_each_patient_only_sees_own_appointment(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            robin = self.login(client, "robin.portal", "Fictional Robin password!")
            casey = self.login(client, "casey.portal", "Fictional Casey password!")
            first = client.get("/portal/appointments", headers=robin)
            second = client.get("/portal/appointments", headers=casey)
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(
                [row["reason_for_visit"] for row in first.json()],
                ["Robin's synthetic follow-up"],
            )
            self.assertEqual(
                [row["reason_for_visit"] for row in second.json()],
                ["Casey's private synthetic appointment"],
            )
            self.assertEqual(first.headers["cache-control"], "no-store")
            self.assertEqual(second.headers["cache-control"], "no-store")
            self.assertEqual(
                set(first.json()[0]),
                {"id", "scheduled_date", "start_time", "reason_for_visit", "status"},
            )
            self.assertNotIn("patient_id", first.text)
            self.assertNotIn("duration_minutes", first.text)
            self.assertNotIn("Casey's private", first.text)

            # Caller-supplied patient IDs do not change the identity-derived scope.
            attempted_override = client.get(
                f"/portal/appointments?patient_id={self.second_id}", headers=robin,
            )
            self.assertEqual(attempted_override.status_code, 200)
            self.assertEqual(attempted_override.json(), first.json())

    def test_missing_invalid_and_non_patient_credentials(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            missing = client.get("/portal/appointments")
            self.assertEqual(missing.status_code, 401)
            self.assertEqual(missing.headers["www-authenticate"], "Bearer")
            self.assertEqual(client.get("/portal/appointments", headers={
                "Authorization": "Bearer invalid",
            }).status_code, 401)
            staff = self.login(client, "clinic.staff", "Fictional staff password!")
            self.assertEqual(client.get("/portal/appointments", headers=staff).status_code, 403)
            self.assertEqual(
                client.get(f"/patients/{self.second_id}/portal-preview/appointments",
                           headers=staff).status_code,
                200,
            )

    def test_patient_session_does_not_unlock_clinical_or_other_portal_routes(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            robin = self.login(client, "robin.portal", "Fictional Robin password!")
            for path in (
                "/patients",
                f"/patients/{self.second_id}/portal-preview/appointments",
                f"/patients/{self.second_id}",
                "/portal/appointments/2",
            ):
                with self.subTest(path=path):
                    self.assertEqual(client.get(path, headers=robin).status_code, 403)
            self.assertEqual(
                client.post("/portal/appointments", headers=robin).status_code, 403
            )

    def test_revoked_expired_and_disabled_sessions(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            robin = self.login(client, "robin.portal", "Fictional Robin password!")
            self.assertEqual(client.get("/portal/appointments", headers=robin).status_code, 200)
            self.assertEqual(client.post("/auth/logout", headers=robin).status_code, 204)
            self.assertEqual(client.get("/portal/appointments", headers=robin).status_code, 401)

            robin = self.login(client, "robin.portal", "Fictional Robin password!")
            with Session(self.engine) as session:
                record = session.query(UserSession).filter_by(revoked_at=None).one()
                record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                session.commit()
            self.assertEqual(client.get("/portal/appointments", headers=robin).status_code, 401)

            robin = self.login(client, "robin.portal", "Fictional Robin password!")
            with Session(self.engine) as session:
                session.query(UserAccount).filter_by(username="robin.portal").one().is_active = False
                session.commit()
            self.assertEqual(client.get("/portal/appointments", headers=robin).status_code, 401)


if __name__ == "__main__":
    unittest.main()
