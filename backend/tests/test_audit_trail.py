"""Privacy-minimal persistent audit events for fictional accounts and charts."""

import unittest
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import AuditEvent, Base, Patient


class AuditTrailTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Fictional", last_name="Patient",
                date_of_birth=date(1990, 1, 1), sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            self.patient_id = patient.id
            for username, account_type, role, patient_id in (
                ("test.clinician", "staff", "clinician", None),
                ("test.desk", "staff", "front_desk", None),
                ("test.patient", "patient", None, patient.id),
            ):
                create_user_account(
                    session, username=username, password="Fictional secure password!",
                    account_type=account_type, staff_role=role, patient_id=patient_id,
                )
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def login(self, client, username):
        response = client.post("/auth/login", json={
            "username": username, "password": "Fictional secure password!",
        })
        self.assertEqual(response.status_code, 200)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def events(self):
        with Session(self.engine) as session:
            return session.scalars(select(AuditEvent).order_by(AuditEvent.id)).all()

    def test_login_outcomes_and_logout_are_persisted_without_credentials(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            denied = client.post("/auth/login", json={
                "username": "bad.login", "password": "A password that must not be kept",
            })
            self.assertEqual(denied.status_code, 401)
            header = self.login(client, "test.patient")
            token = header["Authorization"].split(" ", 1)[1]
            self.assertEqual(client.post("/auth/logout", headers=header).status_code, 204)

        events = self.events()
        self.assertEqual([e.event_type for e in events],
                         ["login_failure", "login_success", "logout"])
        self.assertIsNone(events[0].actor_user_id)
        self.assertIsNone(events[0].subject_patient_id)
        self.assertEqual(events[1].subject_patient_id, self.patient_id)
        self.assertEqual(events[2].actor_user_id, events[1].actor_user_id)
        self.assertEqual([e.status_code for e in events], [401, 200, 204])
        self.assertTrue(all(e.occurred_at for e in events))
        stored = repr([
            (e.event_type, e.route_template, e.actor_user_id,
             e.resource_id, e.status_code, e.subject_patient_id)
            for e in events
        ])
        for forbidden in ("bad.login", "A password", token, "Fictional secure password!"):
            self.assertNotIn(forbidden, stored)

    def test_patient_and_staff_reads_capture_actor_and_target_scope(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            patient_header = self.login(client, "test.patient")
            staff_header = self.login(client, "test.clinician")
            self.assertEqual(
                client.get("/portal/problems?patient_id=888&secret=never-save-this",
                           headers=patient_header).status_code, 200,
            )
            self.assertEqual(
                client.get(f"/patients/{self.patient_id}", headers=staff_header).status_code,
                200,
            )
            self.assertEqual(
                client.get(f"/patients/{self.patient_id}", headers=patient_header).status_code,
                403,
            )
        events = self.events()
        clinical = [event for event in events if event.event_type != "login_success"]
        self.assertEqual([e.event_type for e in clinical],
                         ["clinical_read", "clinical_read", "access_denied"])
        self.assertEqual([e.route_template for e in clinical],
                         ["/portal/problems", "/patients/{patient_id}", "/patients/{patient_id}"])
        self.assertEqual([e.subject_patient_id for e in clinical],
                         [self.patient_id] * 3)
        self.assertIsNone(clinical[0].resource_id)
        self.assertEqual(clinical[1].resource_id, self.patient_id)
        self.assertNotEqual(clinical[0].actor_user_id, clinical[1].actor_user_id)
        self.assertEqual(clinical[0].actor_user_id, clinical[2].actor_user_id)
        self.assertNotIn("never-save-this", repr(clinical))

    def test_denied_anonymous_and_front_desk_access_is_logged(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            self.assertEqual(client.get("/patients").status_code, 401)
            header = self.login(client, "test.desk")
            self.assertEqual(client.get("/patients", headers=header).status_code, 403)
            self.assertEqual(
                client.get("/patients/not-an-id?private=keep-out", headers=header).status_code,
                403,
            )
            self.assertEqual(client.get("/docs").status_code, 200)
            self.assertEqual(client.options("/patients", headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            }).status_code, 200)
        events = self.events()
        self.assertEqual([e.event_type for e in events],
                         ["access_denied", "login_success", "access_denied", "access_denied"])
        self.assertIsNone(events[0].actor_user_id)
        self.assertEqual(events[0].route_template, "/patients")
        self.assertEqual(events[-1].route_template, "/patients/{patient_id}")
        self.assertIsNone(events[-1].resource_id)
        self.assertNotIn("keep-out", repr(events))


if __name__ == "__main__":
    unittest.main()
