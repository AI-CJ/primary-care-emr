"""Administrative archival preserves records and closes existing portal sessions."""

import unittest
from datetime import date, time, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import (
    Appointment, AuditEvent, Base, CareGoal, CareGoalProgress, Patient,
    PatientLifecycleEvent, UserSession,
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


    def test_archived_chart_rejects_staff_demographic_and_scheduling_writes(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            admin = self.login(client, "clinic.admin")
            with Session(self.engine) as session:
                completed_id = session.scalar(select(Appointment.id).where(
                    Appointment.patient_id == self.first_id,
                ))
            self.assertEqual(
                client.post(f"/patients/{self.first_id}/archive", headers=admin).status_code,
                200,
            )
            new_slot = {
                "scheduled_date": (date.today() + timedelta(days=30)).isoformat(),
                "start_time": "11:00:00",
                "reason_for_visit": "Synthetic follow-up",
            }
            demographics = {
                "first_name": "Changed", "last_name": "Example",
                "date_of_birth": "1990-01-01", "sex_at_birth": "unknown",
            }
            denied = client.put(
                f"/patients/{self.first_id}", headers=admin, json=demographics,
            )
            self.assertEqual(denied.status_code, 409)
            self.assertIn("Archived", denied.json()["detail"])

            writes = [
                ("post", f"/patients/{self.first_id}/appointments", new_slot),
                ("put", f"/appointments/{completed_id}", new_slot),
                ("post", f"/appointments/{completed_id}/check-in", None),
                ("post", f"/appointments/{completed_id}/complete", None),
                ("post", f"/appointments/{completed_id}/cancel", None),
                ("post", f"/appointments/{completed_id}/no-show", None),
            ]
            for method, path, payload in writes:
                with self.subTest(path=path):
                    kwargs = {"headers": admin}
                    if payload is not None:
                        kwargs["json"] = payload
                    result = getattr(client, method)(path, **kwargs)
                    self.assertEqual(result.status_code, 409, result.text)
                    self.assertIn("Archived", result.json()["detail"])

            with Session(self.engine) as session:
                self.assertEqual(session.get(Patient, self.first_id).first_name, "Robin")
                visits = session.scalars(select(Appointment).where(
                    Appointment.patient_id == self.first_id,
                )).all()
                self.assertEqual(len(visits), 1)
                self.assertEqual(visits[0].status, "completed")

            # An active chart remains schedulable; reactivation restores access.
            active = client.post(
                f"/patients/{self.second_id}/appointments",
                headers=admin, json=new_slot,
            )
            self.assertEqual(active.status_code, 201, active.text)
            self.assertEqual(
                client.post(f"/patients/{self.first_id}/reactivate",
                            headers=admin).status_code, 200,
            )
            reopened = client.post(
                f"/patients/{self.first_id}/appointments",
                headers=admin, json=new_slot,
            )
            self.assertEqual(reopened.status_code, 201, reopened.text)

    def test_archived_chart_preserves_care_goals_but_blocks_new_writes(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            admin = self.login(client, "clinic.admin")
            old_goal = client.post(
                f"/patients/{self.first_id}/care-goals", headers=admin,
                json={"title": "Synthetic mobility plan"},
            )
            self.assertEqual(old_goal.status_code, 201, old_goal.text)
            goal_id = old_goal.json()["id"]
            other = client.post(
                f"/patients/{self.second_id}/care-goals", headers=admin,
                json={"title": "Synthetic exercise plan"},
            )
            self.assertEqual(other.status_code, 201, other.text)
            other_id = other.json()["id"]
            original = client.post(
                f"/care-goals/{goal_id}/progress", headers=admin,
                json={"note": "Synthetic baseline progress"},
            )
            self.assertEqual(original.status_code, 201, original.text)

            archived = client.post(
                f"/patients/{self.first_id}/archive", headers=admin,
            )
            self.assertEqual(archived.status_code, 200, archived.text)
            goals = client.get(
                f"/patients/{self.first_id}/care-goals", headers=admin,
            )
            self.assertEqual(goals.status_code, 200)
            self.assertEqual([row["id"] for row in goals.json()], [goal_id])
            history = client.get(
                f"/care-goals/{goal_id}/progress", headers=admin,
            )
            self.assertEqual(history.status_code, 200)
            self.assertEqual(len(history.json()), 1)

            active = client.get("/worklists/active-care-goals", headers=admin)
            self.assertEqual(active.status_code, 200)
            active_ids = {item["id"] for item in active.json()}
            self.assertNotIn(goal_id, active_ids)
            self.assertIn(other_id, active_ids)

            denied_writes = [
                (f"/patients/{self.first_id}/care-goals",
                 {"title": "Should not be created"}),
                (f"/care-goals/{goal_id}/complete",
                 {"completion_note": "Should not complete"}),
                (f"/care-goals/{goal_id}/discontinue",
                 {"reason": "Should not discontinue"}),
                (f"/care-goals/{goal_id}/progress",
                 {"note": "Should not append progress"}),
            ]
            for path, payload in denied_writes:
                with self.subTest(path=path):
                    response = client.post(path, headers=admin, json=payload)
                    self.assertEqual(response.status_code, 409, response.text)
                    self.assertIn("Archived", response.json()["detail"])

            with Session(self.engine) as session:
                goals = session.scalars(select(CareGoal).where(
                    CareGoal.patient_id == self.first_id,
                )).all()
                self.assertEqual(len(goals), 1)
                self.assertEqual(goals[0].status, "active")
                self.assertEqual(session.query(CareGoalProgress).filter_by(
                    goal_id=goal_id,
                ).count(), 1)

            # Other active charts remain writable, including by resource ID.
            other_update = client.post(
                f"/care-goals/{other_id}/complete", headers=admin,
                json={"completion_note": "Synthetic outcome"},
            )
            self.assertEqual(other_update.status_code, 200, other_update.text)
            self.assertEqual(
                client.post(
                    f"/patients/{self.first_id}/reactivate", headers=admin,
                ).status_code, 200,
            )
            resumed = client.post(
                f"/care-goals/{goal_id}/progress", headers=admin,
                json={"note": "Synthetic post-reactivation progress"},
            )
            self.assertEqual(resumed.status_code, 201, resumed.text)
            active_again = client.get("/worklists/active-care-goals", headers=admin)
            self.assertIn(goal_id, {item["id"] for item in active_again.json()})


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
