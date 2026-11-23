"""Administrative archival preserves records and closes existing portal sessions."""

import unittest
from datetime import date, time
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import (
    Appointment, AuditEvent, Base, Patient, PatientLifecycleEvent, UserSession,
)


PASSWORD = "Only synthetic test credentials!"


class PatientArchiveLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite://", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            first = Patient(
                first_name="Robin", last_name="Example",
                date_of_birth=date(1990, 1, 1), sex_at_birth="unknown",
            )
            second = Patient(
                first_name="Casey", last_name="Example",
                date_of_birth=date(1992, 2, 2), sex_at_birth="unknown",
            )
            session.add_all([first, second])
            session.flush()
            self.first_id, self.second_id = first.id, second.id
            session.add_all([
                Appointment(
                    patient_id=first.id, scheduled_date=date(2024, 1, 2),
                    start_time=time(9), duration_minutes=30,
                    reason_for_visit="Synthetic completed checkup", status="completed",
                ),
                Appointment(
                    patient_id=second.id, scheduled_date=date(2027, 2, 2),
                    start_time=time(9), duration_minutes=30,
                    reason_for_visit="Synthetic scheduled visit", status="scheduled",
                ),
            ])
            for name, kind, role, patient_id in (
                ("clinic.admin", "staff", "admin", None),
                ("clinic.doctor", "staff", "clinician", None),
                ("robin.portal", "patient", None, first.id),
                ("casey.portal", "patient", None, second.id),
            ):
                create_user_account(
                    session, username=name, password=PASSWORD,
                    account_type=kind, staff_role=role, patient_id=patient_id,
                )
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def login(self, client, username):
        response = client.post(
            "/auth/login", json={"username": username, "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def test_archive_revokes_sessions_preserves_history_and_reactivation(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            admin = self.login(client, "clinic.admin")
            old_token = self.login(client, "robin.portal")
            other = self.login(client, "casey.portal")
            self.assertEqual(
                client.get("/portal/appointments", headers=old_token).status_code, 200,
            )
            result = client.post(
                f"/patients/{self.first_id}/archive", headers=admin,
            )
            self.assertEqual(result.status_code, 200)
            self.assertIsNotNone(result.json()["archived_at"])
            self.assertEqual(result.headers["cache-control"], "no-store")
            self.assertEqual(
                client.get("/portal/appointments", headers=old_token).status_code, 401,
            )
            self.assertEqual(
                client.get("/auth/me", headers=old_token).status_code, 401,
            )
            self.assertEqual(client.post(
                "/auth/login",
                json={"username": "robin.portal", "password": PASSWORD},
            ).status_code, 401)
            self.assertEqual(
                client.get("/portal/appointments", headers=other).status_code, 200,
            )

            # Staff can still retrieve the historical chart; no destructive delete.
            chart = client.get(f"/patients/{self.first_id}", headers=admin)
            self.assertEqual(chart.status_code, 200)
            self.assertIsNotNone(chart.json()["archived_at"])
            history = client.get(
                f"/patients/{self.first_id}/appointments", headers=admin,
            )
            self.assertEqual(history.status_code, 200)
            self.assertEqual(len(history.json()), 1)
            with Session(self.engine) as session:
                self.assertEqual(
                    session.scalar(select(Appointment).where(
                        Appointment.patient_id == self.first_id,
                    )).status, "completed",
                )
                self.assertIsNotNone(session.scalar(
                    select(UserSession).where(UserSession.revoked_at.is_not(None))
                ))
                with self.assertRaisesRegex(ValueError, "Archived patient"):
                    create_user_account(
                        session, username="robin.second", password=PASSWORD,
                        account_type="patient", patient_id=self.first_id,
                    )

            resumed = client.post(
                f"/patients/{self.first_id}/reactivate", headers=admin,
            )
            self.assertEqual(resumed.status_code, 200)
            self.assertIsNone(resumed.json()["archived_at"])
            self.assertEqual(
                client.get("/auth/me", headers=old_token).status_code, 401,
            )
            self.login(client, "robin.portal")

            changes = client.get(
                f"/patients/{self.first_id}/lifecycle", headers=admin,
            )
            self.assertEqual(changes.status_code, 200)
            self.assertEqual(
                [row["action"] for row in changes.json()],
                ["reactivate", "archive"],
            )
            self.assertTrue(all("password" not in row for row in changes.json()))
            with Session(self.engine) as session:
                self.assertEqual(
                    session.query(PatientLifecycleEvent).filter_by(
                        patient_id=self.first_id,
                    ).count(), 2,
                )
                paths = session.scalars(select(AuditEvent.route_template).where(
                    AuditEvent.route_template.like("/patients/%"),
                )).all()
                self.assertIn("/patients/{patient_id}/archive", paths)

    def test_pending_appointments_and_duplicate_transitions_rejected(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            admin = self.login(client, "clinic.admin")
            blocked = client.post(
                f"/patients/{self.second_id}/archive", headers=admin,
            )
            self.assertEqual(blocked.status_code, 409)
            self.assertIn("appointments", blocked.json()["detail"])
            self.assertEqual(
                client.post(f"/patients/{self.first_id}/reactivate", headers=admin).status_code,
                409,
            )
            self.assertEqual(
                client.post(f"/patients/99999/archive", headers=admin).status_code,
                404,
            )
            self.assertEqual(
                client.post(f"/patients/{self.first_id}/archive", headers=admin).status_code,
                200,
            )
            self.assertEqual(
                client.post(f"/patients/{self.first_id}/archive", headers=admin).status_code,
                409,
            )
            with Session(self.engine) as session:
                self.assertEqual(
                    session.query(PatientLifecycleEvent).count(), 1,
                )

    def test_only_admin_can_change_or_read_lifecycle(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            doctor = self.login(client, "clinic.doctor")
            patient = self.login(client, "robin.portal")
            for path in (
                f"/patients/{self.first_id}/archive",
                f"/patients/{self.first_id}/reactivate",
            ):
                for headers, status in ((doctor, 403), (patient, 403), (None, 401)):
                    self.assertEqual(
                        client.post(path, headers=headers).status_code, status,
                    )
            for headers, status in ((doctor, 403), (patient, 403), (None, 401)):
                self.assertEqual(
                    client.get(
                        f"/patients/{self.first_id}/lifecycle", headers=headers,
                    ).status_code, status,
                )
            with Session(self.engine) as session:
                self.assertIsNone(session.get(Patient, self.first_id).archived_at)
                self.assertEqual(session.query(PatientLifecycleEvent).count(), 0)


if __name__ == "__main__":
    unittest.main()
