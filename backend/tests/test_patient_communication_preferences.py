"""Patient communication choices stay scoped to the authenticated identity."""

import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.communication_preferences import (
    CommunicationPreferencesPayload, replace_communication_preferences,
)
from backend.main import app
from backend.models import AuditEvent, Base, Patient, PatientCommunicationPreference


class PatientCommunicationPreferencesTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            first = Patient(
                first_name="Robin", last_name="Fictional",
                date_of_birth=date(1990, 1, 1), sex_at_birth="unknown",
            )
            second = Patient(
                first_name="Casey", last_name="Fictional",
                date_of_birth=date(1992, 2, 2), sex_at_birth="unknown",
            )
            session.add_all([first, second])
            session.flush()
            self.first_id, self.second_id = first.id, second.id
            for username, kind, role, patient_id in (
                ("robin.portal", "patient", None, first.id),
                ("casey.portal", "patient", None, second.id),
                ("demo.clinician", "staff", "clinician", None),
                ("demo.admin", "staff", "admin", None),
            ):
                create_user_account(
                    session, username=username, password="Fictional test password!",
                    account_type=kind, staff_role=role, patient_id=patient_id,
                )
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def login(self, client, username):
        response = client.post("/auth/login", json={
            "username": username, "password": "Fictional test password!",
        })
        self.assertEqual(response.status_code, 200)
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def test_defaults_update_persistence_and_ownership(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            robin = self.login(client, "robin.portal")
            casey = self.login(client, "casey.portal")
            defaults = {
                "preferred_channel": "portal",
                "appointment_reminders": False,
                "care_updates": False,
            }
            first = client.get("/portal/communication-preferences", headers=robin)
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.headers["cache-control"], "no-store")
            self.assertEqual(first.json(), defaults)
            with Session(self.engine) as session:
                self.assertEqual(session.query(PatientCommunicationPreference).count(), 0)

            chosen = {
                "preferred_channel": "phone",
                "appointment_reminders": True,
                "care_updates": False,
            }
            saved = client.put(
                "/portal/communication-preferences", json=chosen, headers=robin,
            )
            self.assertEqual(saved.status_code, 200)
            self.assertEqual(saved.headers["cache-control"], "no-store")
            self.assertEqual(saved.json(), chosen)
            self.assertEqual(
                client.get("/portal/communication-preferences", headers=robin).json(),
                chosen,
            )
            self.assertEqual(
                client.get("/portal/communication-preferences", headers=casey).json(),
                defaults,
            )
            override = {
                "preferred_channel": "email",
                "appointment_reminders": False,
                "care_updates": True,
            }
            response = client.put(
                f"/portal/communication-preferences?patient_id={self.second_id}",
                json=override, headers=robin,
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), override)
            self.assertEqual(
                client.get("/portal/communication-preferences", headers=casey).json(),
                defaults,
            )
            with Session(self.engine) as session:
                rows = session.scalars(select(PatientCommunicationPreference)).all()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].patient_id, self.first_id)
                self.assertEqual(rows[0].preferred_channel, "email")

    def test_archived_chart_blocks_preference_write_after_authorization(self):
        # Exercise the write service directly to model an archive occurring
        # after the HTTP authorization check but before the write transaction.
        initial = CommunicationPreferencesPayload(
            preferred_channel="portal", appointment_reminders=False, care_updates=False,
        )
        changed = CommunicationPreferencesPayload(
            preferred_channel="email", appointment_reminders=True, care_updates=True,
        )
        with Session(self.engine) as session:
            replace_communication_preferences(session, self.first_id, initial)
            patient = session.get(Patient, self.first_id)
            patient.archived_at = datetime.now(timezone.utc)
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as denied:
                replace_communication_preferences(session, self.first_id, changed)
            self.assertEqual(denied.exception.status_code, 409)
            session.rollback()
            saved = session.get(PatientCommunicationPreference, self.first_id)
            self.assertEqual(saved.preferred_channel, "portal")
            self.assertFalse(saved.appointment_reminders)
            self.assertFalse(saved.care_updates)
            replace_communication_preferences(session, self.second_id, changed)
            patient = session.get(Patient, self.first_id)
            patient.archived_at = None
            session.commit()
            self.assertEqual(
                replace_communication_preferences(session, self.first_id, changed), changed,
            )

    def test_bad_payloads_do_not_replace_saved_choices(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            robin = self.login(client, "robin.portal")
            valid = {
                "preferred_channel": "portal",
                "appointment_reminders": True,
                "care_updates": True,
            }
            self.assertEqual(client.put(
                "/portal/communication-preferences", json=valid, headers=robin,
            ).status_code, 200)
            for invalid in (
                {**valid, "preferred_channel": "sms"},
                {**valid, "appointment_reminders": "not-a-boolean"},
                {**valid, "patient_id": self.second_id},
                {"preferred_channel": "phone"},
            ):
                with self.subTest(invalid=invalid):
                    response = client.put(
                        "/portal/communication-preferences", json=invalid, headers=robin,
                    )
                    self.assertEqual(response.status_code, 422)
                    self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(
                client.get("/portal/communication-preferences", headers=robin).json(),
                valid,
            )

    def test_access_controls_for_both_http_methods(self):
        payload = {
            "preferred_channel": "email",
            "appointment_reminders": True,
            "care_updates": True,
        }
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            for method in ("get", "put"):
                kwargs = {"json": payload} if method == "put" else {}
                for headers in (None, {"Authorization": "Bearer wrong"}):
                    response = getattr(client, method)(
                        "/portal/communication-preferences", headers=headers, **kwargs,
                    )
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.headers["cache-control"], "no-store")
                for username in ("demo.clinician", "demo.admin"):
                    response = getattr(client, method)(
                        "/portal/communication-preferences",
                        headers=self.login(client, username), **kwargs,
                    )
                    self.assertEqual(response.status_code, 403)
            robin = self.login(client, "robin.portal")
            self.assertEqual(client.post(
                "/portal/communication-preferences", json=payload,
                headers=robin,
            ).status_code, 403)
        with Session(self.engine) as session:
            self.assertEqual(session.query(PatientCommunicationPreference).count(), 0)

    def test_preferences_are_not_in_audit_metadata(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            robin = self.login(client, "robin.portal")
            client.put(
                "/portal/communication-preferences?secret=omit-from-audit",
                json={
                    "preferred_channel": "phone",
                    "appointment_reminders": True,
                    "care_updates": True,
                }, headers=robin,
            )
            client.get("/portal/communication-preferences", headers=robin)
            client.get("/portal/communication-preferences")
        with Session(self.engine) as session:
            events = session.scalars(select(AuditEvent).where(
                AuditEvent.route_template == "/portal/communication-preferences"
            ).order_by(AuditEvent.id)).all()
            self.assertEqual(
                [(event.event_type, event.status_code) for event in events],
                [("clinical_write", 200), ("clinical_read", 200),
                 ("access_denied", 401)],
            )
            self.assertEqual(events[0].subject_patient_id, self.first_id)
            self.assertTrue(all(event.resource_id is None for event in events))
            self.assertNotIn("omit-from-audit", repr(events))
            self.assertNotIn("Fictional test password!", repr(events))


if __name__ == "__main__":
    unittest.main()
