"""Administrative archival preserves records and closes existing portal sessions."""

import unittest
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import (
    Appointment, AuditEvent, Base, CareGoal, CareGoalProgress, Encounter,
    LabOrder, LabResult, Patient, PatientLifecycleEvent, Referral, UserSession,
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


    def test_archived_follow_up_tasks_preserve_history_and_leave_worklist(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            admin = self.login(client, "clinic.admin")
            chart = f"/patients/{self.first_id}/follow-up-tasks"
            other_chart = f"/patients/{self.second_id}/follow-up-tasks"
            first = client.post(chart, headers=admin, json={
                "title": "Synthetic follow-up", "due_date": "2027-01-10",
            })
            self.assertEqual(first.status_code, 201, first.text)
            task_id = first.json()["id"]
            other = client.post(other_chart, headers=admin, json={
                "title": "Other synthetic follow-up",
            })
            self.assertEqual(other.status_code, 201, other.text)
            other_id = other.json()["id"]
            task = f"/follow-up-tasks/{task_id}"
            original = client.post(task + "/reschedule", headers=admin, json={
                "due_date": "2027-01-12", "reason": "Synthetic scheduling change",
            })
            self.assertEqual(original.status_code, 200, original.text)
            before = client.get(chart, headers=admin).json()
            history = client.get(task + "/due-date-changes", headers=admin).json()
            self.assertEqual(len(history), 1)

            archived = client.post(
                f"/patients/{self.first_id}/archive", headers=admin,
            )
            self.assertEqual(archived.status_code, 200, archived.text)
            writes = [
                (chart, {"title": "Blocked synthetic follow-up"}),
                (task + "/complete", {"completion_note": "Blocked completion"}),
                (task + "/cancel", {"reason": "Blocked cancellation"}),
                (task + "/reschedule", {
                    "due_date": "2027-01-15", "reason": "Blocked date change",
                }),
            ]
            for path, payload in writes:
                with self.subTest(path=path):
                    response = client.post(path, headers=admin, json=payload)
                    self.assertEqual(response.status_code, 409, response.text)
                    self.assertIn("Archived", response.json()["detail"])

            saved = client.get(chart, headers=admin)
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertEqual(saved.json(), before)
            saved_history = client.get(task + "/due-date-changes", headers=admin)
            self.assertEqual(saved_history.status_code, 200, saved_history.text)
            self.assertEqual(saved_history.json(), history)
            queue_path = "/worklists/open-follow-up-tasks"
            queue = client.get(queue_path, headers=admin)
            self.assertEqual(queue.status_code, 200, queue.text)
            self.assertEqual({row["id"] for row in queue.json()}, {other_id})

            other_change = client.post(
                f"/follow-up-tasks/{other_id}/complete", headers=admin,
                json={"completion_note": "Synthetic outcome"},
            )
            self.assertEqual(other_change.status_code, 200, other_change.text)
            resumed = client.post(
                f"/patients/{self.first_id}/reactivate", headers=admin,
            )
            self.assertEqual(resumed.status_code, 200, resumed.text)
            queue = client.get(queue_path, headers=admin)
            self.assertEqual(queue.status_code, 200, queue.text)
            self.assertEqual({row["id"] for row in queue.json()}, {task_id})
            changed = client.post(task + "/reschedule", headers=admin, json={
                "due_date": "2027-01-15", "reason": "Synthetic resumed follow-up",
            })
            self.assertEqual(changed.status_code, 200, changed.text)
            self.assertEqual(
                len(client.get(task + "/due-date-changes", headers=admin).json()), 2,
            )

    def test_archived_lab_orders_preserve_history_and_leave_worklists(self):
        visit_date = date(2024, 1, 2)
        with Session(self.engine) as session:
            draft = Encounter(
                patient_id=self.first_id, visit_date=visit_date,
                reason_for_visit="Synthetic draft",
            )
            finalized = Encounter(
                patient_id=self.first_id, visit_date=visit_date,
                reason_for_visit="Synthetic finalized visit",
                finalized_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
            )
            other = Encounter(
                patient_id=self.second_id, visit_date=visit_date,
                reason_for_visit="Other synthetic visit",
                finalized_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
            )
            session.add_all([draft, finalized, other])
            session.flush()
            draft_id = draft.id
            orders = [
                LabOrder(encounter_id=visit.id, test_name=name,
                         priority="routine", status=status)
                for visit, name, status in (
                    (finalized, "Synthetic cancellation", "ordered"),
                    (finalized, "Synthetic collection", "ordered"),
                    (finalized, "Synthetic unreleased result", "resulted"),
                    (other, "Other pending test", "ordered"),
                    (other, "Other unreleased result", "resulted"),
                )
            ]
            session.add_all(orders)
            session.flush()
            cancel_id, record_id, release_id, other_pending, other_release = (
                order.id for order in orders
            )
            for order_id in (release_id, other_release):
                session.add(LabResult(
                    lab_order_id=order_id, collected_on=visit_date,
                    result_text="Synthetic result",
                ))
            session.commit()

        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            admin = self.login(client, "clinic.admin")
            chart = f"/patients/{self.first_id}/lab-orders"
            history = client.get(chart, headers=admin)
            self.assertEqual(history.status_code, 200, history.text)
            before = history.json()
            self.assertEqual(len(before), 3)
            result_path = f"/lab-orders/{release_id}/result"
            original_result = client.get(result_path, headers=admin)
            self.assertEqual(original_result.status_code, 200, original_result.text)
            pending_path = "/worklists/pending-lab-orders"
            unreleased_path = "/worklists/unreleased-lab-results"

            def queue_ids(path, key):
                response = client.get(path, headers=admin)
                self.assertEqual(response.status_code, 200, response.text)
                return {row[key] for row in response.json()}

            self.assertEqual(
                queue_ids(pending_path, "id"), {cancel_id, record_id, other_pending},
            )
            self.assertEqual(
                queue_ids(unreleased_path, "order_id"), {release_id, other_release},
            )
            archived = client.post(
                f"/patients/{self.first_id}/archive", headers=admin,
            )
            self.assertEqual(archived.status_code, 200, archived.text)
            writes = [
                (f"/encounters/{draft_id}/lab-orders",
                 {"test_name": "Synthetic new order"}, 201),
                (f"/lab-orders/{cancel_id}/cancel",
                 {"reason": "Synthetic cancellation"}, 200),
                (f"/lab-orders/{record_id}/result",
                 {"collected_on": visit_date.isoformat(),
                  "result_text": "Synthetic collection"}, 201),
                (result_path + "/release", None, 200),
            ]
            for path, payload, _ in writes:
                with self.subTest(path=path):
                    kwargs = {"headers": admin}
                    if payload is not None:
                        kwargs["json"] = payload
                    response = client.post(path, **kwargs)
                    self.assertEqual(response.status_code, 409, response.text)
                    self.assertIn("Archived", response.json()["detail"])

            saved = client.get(chart, headers=admin)
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertEqual(saved.json(), before)
            saved_result = client.get(result_path, headers=admin)
            self.assertEqual(saved_result.status_code, 200, saved_result.text)
            self.assertEqual(saved_result.json(), original_result.json())
            self.assertEqual(queue_ids(pending_path, "id"), {other_pending})
            self.assertEqual(queue_ids(unreleased_path, "order_id"), {other_release})

            active_write = client.post(
                f"/lab-orders/{other_pending}/cancel", headers=admin,
                json={"reason": "Synthetic active chart cancellation"},
            )
            self.assertEqual(active_write.status_code, 200, active_write.text)
            active_release = client.post(
                f"/lab-orders/{other_release}/result/release", headers=admin,
            )
            self.assertEqual(active_release.status_code, 200, active_release.text)

            resumed = client.post(
                f"/patients/{self.first_id}/reactivate", headers=admin,
            )
            self.assertEqual(resumed.status_code, 200, resumed.text)
            self.assertEqual(queue_ids(pending_path, "id"), {cancel_id, record_id})
            self.assertEqual(queue_ids(unreleased_path, "order_id"), {release_id})
            for path, payload, status in writes:
                with self.subTest(reactivated=path):
                    kwargs = {"headers": admin}
                    if payload is not None:
                        kwargs["json"] = payload
                    response = client.post(path, **kwargs)
                    self.assertEqual(response.status_code, status, response.text)


    def test_archived_referrals_preserve_history_and_leave_worklist(self):
        visit_date = date(2024, 1, 2)
        with Session(self.engine) as session:
            draft = Encounter(
                patient_id=self.first_id, visit_date=visit_date,
                reason_for_visit="Synthetic draft",
            )
            finalized = Encounter(
                patient_id=self.first_id, visit_date=visit_date,
                reason_for_visit="Synthetic finalized visit",
                finalized_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
            )
            other = Encounter(
                patient_id=self.second_id, visit_date=visit_date,
                reason_for_visit="Other synthetic visit",
                finalized_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
            )
            session.add_all([draft, finalized, other])
            session.flush()
            draft_id = draft.id
            referrals = [
                Referral(
                    encounter_id=visit.id, specialty=specialty,
                    reason="Synthetic referral", priority="routine", status="requested",
                )
                for visit, specialty in (
                    (finalized, "Synthetic cancellation"),
                    (finalized, "Synthetic completion"),
                    (other, "Other pending referral"),
                )
            ]
            session.add_all(referrals)
            session.flush()
            cancel_id, complete_id, other_id = (row.id for row in referrals)
            session.commit()

        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            admin = self.login(client, "clinic.admin")
            chart = f"/patients/{self.first_id}/referrals"
            queue_path = "/worklists/pending-referrals"

            def queue_ids():
                response = client.get(queue_path, headers=admin)
                self.assertEqual(response.status_code, 200, response.text)
                return {row["id"] for row in response.json()}

            history = client.get(chart, headers=admin)
            self.assertEqual(history.status_code, 200, history.text)
            before = history.json()
            self.assertEqual(len(before), 2)
            self.assertEqual(queue_ids(), {cancel_id, complete_id, other_id})

            archived = client.post(
                f"/patients/{self.first_id}/archive", headers=admin,
            )
            self.assertEqual(archived.status_code, 200, archived.text)
            writes = [
                (f"/encounters/{draft_id}/referrals",
                 {"specialty": "Synthetic new referral", "reason": "Synthetic reason"}, 201),
                (f"/referrals/{cancel_id}/cancel",
                 {"reason": "Synthetic cancellation"}, 200),
                (f"/referrals/{complete_id}/complete",
                 {"seen_on": visit_date.isoformat(),
                  "follow_up_summary": "Synthetic outcome"}, 200),
            ]
            for path, payload, _ in writes:
                with self.subTest(path=path):
                    result = client.post(path, headers=admin, json=payload)
                    self.assertEqual(result.status_code, 409, result.text)
                    self.assertIn("Archived", result.json()["detail"])

            saved = client.get(chart, headers=admin)
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertEqual(saved.json(), before)
            self.assertEqual(queue_ids(), {other_id})
            active_write = client.post(
                f"/referrals/{other_id}/complete", headers=admin,
                json={"seen_on": visit_date.isoformat(),
                      "follow_up_summary": "Other synthetic outcome"},
            )
            self.assertEqual(active_write.status_code, 200, active_write.text)

            resumed = client.post(
                f"/patients/{self.first_id}/reactivate", headers=admin,
            )
            self.assertEqual(resumed.status_code, 200, resumed.text)
            self.assertEqual(queue_ids(), {cancel_id, complete_id})
            for path, payload, status in writes:
                with self.subTest(reactivated=path):
                    result = client.post(path, headers=admin, json=payload)
                    self.assertEqual(result.status_code, status, result.text)
            with Session(self.engine) as session:
                self.assertEqual(session.get(Referral, cancel_id).status, "cancelled")
                self.assertEqual(session.get(Referral, complete_id).status, "completed")

    def test_archived_patient_clinical_records_preserve_history(self):
        cases = (
            ("problems", {"name": "Synthetic condition"},
             {"name": "Synthetic revised condition", "status": "resolved"}),
            ("medications", {"name": "Synthetic medication"},
             {"name": "Synthetic revised medication", "status": "discontinued"}),
            ("allergies", {"allergen": "Synthetic allergen"},
             {"allergen": "Synthetic revised allergen", "status": "inactive"}),
            ("vitals", {"recorded_on": "2024-01-02", "heart_rate": 72},
             {"recorded_on": "2024-01-02", "heart_rate": 80}),
        )
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            admin = self.login(client, "clinic.admin")
            doctor = self.login(client, "clinic.doctor")

            def chart_path(patient_id, kind):
                return f"/patients/{patient_id}/{kind}"

            def read_chart(patient_id, kind):
                result = client.get(chart_path(patient_id, kind), headers=doctor)
                self.assertEqual(result.status_code, 200, result.text)
                return result.json()

            first_ids, other_ids, before = {}, {}, {}
            for kind, initial, _ in cases:
                for patient_id, ids in (
                    (self.first_id, first_ids), (self.second_id, other_ids),
                ):
                    result = client.post(
                        chart_path(patient_id, kind), headers=doctor, json=initial,
                    )
                    self.assertEqual(result.status_code, 201, result.text)
                    ids[kind] = result.json()["id"]
                before[kind] = read_chart(self.first_id, kind)
                self.assertEqual(len(before[kind]), 1)

            archived = client.post(
                f"/patients/{self.first_id}/archive", headers=admin,
            )
            self.assertEqual(archived.status_code, 200, archived.text)

            for kind, initial, changed in cases:
                with self.subTest(kind=kind):
                    path = chart_path(self.first_id, kind)
                    resource = f"/{kind}/{first_ids[kind]}"
                    for headers in (doctor, admin):
                        for result in (
                            client.post(path, headers=headers, json=initial),
                            client.put(resource, headers=headers, json=changed),
                        ):
                            self.assertEqual(result.status_code, 409, result.text)
                            self.assertIn("Archived", result.json()["detail"])
                    self.assertEqual(read_chart(self.first_id, kind), before[kind])

                    other_update = client.put(
                        f"/{kind}/{other_ids[kind]}", headers=doctor, json=changed,
                    )
                    self.assertEqual(other_update.status_code, 200, other_update.text)
                    for field, value in changed.items():
                        self.assertEqual(other_update.json()[field], value)
                    other_create = client.post(
                        chart_path(self.second_id, kind), headers=doctor, json=initial,
                    )
                    self.assertEqual(other_create.status_code, 201, other_create.text)

            resumed = client.post(
                f"/patients/{self.first_id}/reactivate", headers=admin,
            )
            self.assertEqual(resumed.status_code, 200, resumed.text)
            for kind, initial, changed in cases:
                with self.subTest(reactivated=kind):
                    updated = client.put(
                        f"/{kind}/{first_ids[kind]}", headers=doctor, json=changed,
                    )
                    self.assertEqual(updated.status_code, 200, updated.text)
                    self.assertEqual(updated.json()["id"], first_ids[kind])
                    for field, value in changed.items():
                        self.assertEqual(updated.json()[field], value)
                    created = client.post(
                        chart_path(self.first_id, kind), headers=doctor, json=initial,
                    )
                    self.assertEqual(created.status_code, 201, created.text)
                    self.assertEqual(len(read_chart(self.first_id, kind)), 2)

    def test_archived_visit_notes_and_addenda_preserve_history(self):
        note = {
            "visit_date": "2024-01-02",
            "reason_for_visit": "Synthetic visit",
            "assessment": "Synthetic assessment",
            "plan": "Synthetic plan",
        }
        changed = {**note, "assessment": "Revised synthetic assessment"}
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            admin = self.login(client, "clinic.admin")
            doctor = self.login(client, "clinic.doctor")

            def create(patient_id, payload):
                result = client.post(
                    f"/patients/{patient_id}/encounters", headers=doctor, json=payload,
                )
                self.assertEqual(result.status_code, 201, result.text)
                return result.json()["id"]

            def read(path):
                result = client.get(path, headers=doctor)
                self.assertEqual(result.status_code, 200, result.text)
                return result.json()

            with Session(self.engine) as session:
                appointment_id = session.scalar(select(Appointment.id).where(
                    Appointment.patient_id == self.first_id,
                ))
            draft_id = create(self.first_id, note)
            final_id = create(self.first_id, note)
            self.assertEqual(client.post(
                f"/encounters/{final_id}/finalize", headers=doctor,
            ).status_code, 200)
            addenda = f"/encounters/{final_id}/addenda"
            self.assertEqual(client.post(
                addenda, headers=doctor, json={"content": "Original synthetic addendum"},
            ).status_code, 201)
            chart = f"/patients/{self.first_id}/encounters"
            before_notes = read(chart)
            before_addenda = read(addenda)
            self.assertEqual(len(before_notes), 2)
            self.assertEqual(len(before_addenda), 1)

            archived = client.post(f"/patients/{self.first_id}/archive", headers=admin)
            self.assertEqual(archived.status_code, 200, archived.text)

            writes = (
                ("post", chart, note, 201),
                ("post", chart, {**note, "appointment_id": appointment_id}, 201),
                ("put", f"/encounters/{draft_id}", changed, 200),
                ("post", f"/encounters/{draft_id}/finalize", None, 200),
                ("post", addenda, {"content": "Second synthetic addendum"}, 201),
            )

            def write(case, headers):
                method, path, payload, _ = case
                kwargs = {"headers": headers}
                if payload is not None:
                    kwargs["json"] = payload
                return getattr(client, method)(path, **kwargs)

            for headers in (doctor, admin):
                for case in writes:
                    with self.subTest(archived=case[1], payload=case[2]):
                        denied = write(case, headers)
                        self.assertEqual(denied.status_code, 409, denied.text)
                        self.assertIn("Archived", denied.json()["detail"])
            self.assertEqual(read(chart), before_notes)
            self.assertEqual(read(addenda), before_addenda)

            # Archiving one chart does not prevent another chart's visit workflow.
            other_id = create(self.second_id, note)
            for case in (
                ("put", f"/encounters/{other_id}", changed, 200),
                ("post", f"/encounters/{other_id}/finalize", None, 200),
                ("post", f"/encounters/{other_id}/addenda",
                 {"content": "Other synthetic addendum"}, 201),
            ):
                result = write(case, doctor)
                self.assertEqual(result.status_code, case[3], result.text)

            resumed = client.post(
                f"/patients/{self.first_id}/reactivate", headers=admin,
            )
            self.assertEqual(resumed.status_code, 200, resumed.text)
            for case in writes:
                with self.subTest(reactivated=case[1], payload=case[2]):
                    result = write(case, doctor)
                    self.assertEqual(result.status_code, case[3], result.text)
            # Reactivation does not make a finalized note editable.
            result = client.put(
                f"/encounters/{final_id}", headers=doctor, json=changed,
            )
            self.assertEqual(result.status_code, 409, result.text)
            self.assertIn("Finalized", result.json()["detail"])
            after = {row["id"]: row for row in read(chart)}
            self.assertEqual(len(after), 4)
            original_final = next(row for row in before_notes if row["id"] == final_id)
            self.assertEqual(after[final_id], original_final)
            self.assertEqual(after[draft_id]["assessment"], changed["assessment"])
            self.assertIsNotNone(after[draft_id]["finalized_at"])
            self.assertEqual(read(addenda)[:1], before_addenda)
            self.assertEqual(len(read(addenda)), 2)

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
