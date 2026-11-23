
"""Patient appointment requests never mutate visits and remain identity-scoped."""

import unittest
from datetime import date, timedelta, time
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import (
    Appointment, AppointmentChangeRequest, AuditEvent, Base, Patient,
)


class PatientAppointmentChangeRequestTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite://", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            first = Patient(first_name="Robin", last_name="Synthetic",
                            date_of_birth=date(1990, 1, 2), sex_at_birth="unknown")
            second = Patient(first_name="Casey", last_name="Synthetic",
                             date_of_birth=date(1992, 2, 3), sex_at_birth="unknown")
            session.add_all([first, second])
            session.flush()
            self.first_id, self.second_id = first.id, second.id
            future = date.today() + timedelta(days=14)
            past = date.today() - timedelta(days=14)
            appointments = [
                Appointment(patient_id=first.id, scheduled_date=future,
                            start_time=time(10), duration_minutes=30,
                            reason_for_visit="Private synthetic visit A", status="scheduled"),
                Appointment(patient_id=second.id, scheduled_date=future,
                            start_time=time(11), duration_minutes=30,
                            reason_for_visit="Private synthetic visit B", status="scheduled"),
                Appointment(patient_id=first.id, scheduled_date=past,
                            start_time=time(9), duration_minutes=30,
                            reason_for_visit="Old synthetic visit", status="scheduled"),
                Appointment(patient_id=first.id, scheduled_date=future,
                            start_time=time(14), duration_minutes=30,
                            reason_for_visit="Finished synthetic visit", status="completed"),
            ]
            session.add_all(appointments)
            session.flush()
            self.first_appointment, self.second_appointment = appointments[0].id, appointments[1].id
            self.past_appointment, self.finished_appointment = appointments[2].id, appointments[3].id
            for username, account_type, staff_role, patient_id in (
                ("robin.portal", "patient", None, first.id),
                ("casey.portal", "patient", None, second.id),
                ("clinic.clinician", "staff", "clinician", None),
                ("clinic.admin", "staff", "admin", None),
            ):
                create_user_account(session, username=username,
                                    password="Synthetic test password!",
                                    account_type=account_type, staff_role=staff_role,
                                    patient_id=patient_id)
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def login(self, client, username):
        response = client.post("/auth/login", json={
            "username": username, "password": "Synthetic test password!",
        })
        self.assertEqual(response.status_code, 200)
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def test_patient_submission_and_staff_review_do_not_change_schedule(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            robin = self.login(client, "robin.portal")
            casey = self.login(client, "casey.portal")
            staff = self.login(client, "clinic.clinician")
            submitted = client.post("/portal/appointment-change-requests",
                                    json={"appointment_id": self.first_appointment,
                                          "kind": "reschedule"}, headers=robin)
            self.assertEqual(submitted.status_code, 201)
            self.assertEqual(submitted.headers["cache-control"], "no-store")
            self.assertEqual(submitted.json()["status"], "pending")
            self.assertNotIn("patient_id", submitted.json())
            self.assertNotIn("Private synthetic visit", submitted.text)
            self.assertEqual(client.get("/portal/appointment-change-requests",
                                        headers=casey).json(), [])
            own = client.get("/portal/appointment-change-requests", headers=robin)
            self.assertEqual(len(own.json()), 1)
            self.assertEqual(own.json()[0]["appointment_id"], self.first_appointment)
            self.assertEqual(own.headers["cache-control"], "no-store")
            queue = client.get("/worklists/appointment-change-requests", headers=staff)
            self.assertEqual(queue.status_code, 200)
            self.assertEqual(len(queue.json()), 1)
            self.assertEqual(queue.json()[0]["patient_id"], self.first_id)
            request_id = submitted.json()["id"]
            reviewed = client.post(f"/appointment-change-requests/{request_id}/review",
                                   headers=staff)
            self.assertEqual(reviewed.status_code, 200)
            self.assertEqual(reviewed.json()["status"], "reviewed")
            self.assertIsNotNone(reviewed.json()["reviewed_at"])
            self.assertEqual(client.get("/worklists/appointment-change-requests",
                                        headers=staff).json(), [])
            self.assertEqual(client.get("/portal/appointment-change-requests",
                                        headers=robin).json()[0]["status"], "reviewed")
            self.assertEqual(client.post(f"/appointment-change-requests/{request_id}/review",
                                         headers=staff).status_code, 409)
        with Session(self.engine) as session:
            appointment = session.get(Appointment, self.first_appointment)
            self.assertEqual(appointment.status, "scheduled")
            self.assertEqual(appointment.start_time, time(10))
            self.assertEqual(session.query(AppointmentChangeRequest).count(), 1)

    def test_ownership_eligibility_duplicate_and_validation(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            robin = self.login(client, "robin.portal")
            payload = {"appointment_id": self.first_appointment, "kind": "cancel"}
            for appointment_id, expected in (
                (self.second_appointment, 404),
                (999999, 404),
                (self.past_appointment, 409),
                (self.finished_appointment, 409),
            ):
                result = client.post("/portal/appointment-change-requests",
                                     json={**payload, "appointment_id": appointment_id},
                                     headers=robin)
                self.assertEqual(result.status_code, expected)
            for bad in (
                {**payload, "kind": "delete"},
                {**payload, "patient_id": self.second_id},
                {**payload, "appointment_id": -1},
                {"kind": "cancel"},
            ):
                self.assertEqual(client.post("/portal/appointment-change-requests",
                                             json=bad, headers=robin).status_code, 422)
            self.assertEqual(client.post("/portal/appointment-change-requests",
                                         json=payload, headers=robin).status_code, 201)
            self.assertEqual(client.post("/portal/appointment-change-requests",
                                         json=payload, headers=robin).status_code, 409)
            # Query parameters cannot override the authenticated patient.
            result = client.get("/portal/appointment-change-requests",
                                params={"patient_id": self.second_id}, headers=robin)
            self.assertEqual(len(result.json()), 1)
        with Session(self.engine) as session:
            self.assertEqual(session.query(AppointmentChangeRequest).count(), 1)

    def test_access_controls_and_privacy_audit(self):
        path = "/portal/appointment-change-requests"
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            for method in ("get", "post"):
                kwargs = {"json": {"appointment_id": self.first_appointment,
                                   "kind": "cancel"}} if method == "post" else {}
                for headers in (None, {"Authorization": "Bearer invalid"}):
                    result = getattr(client, method)(path, headers=headers, **kwargs)
                    self.assertEqual(result.status_code, 401)
                    self.assertEqual(result.headers["cache-control"], "no-store")
                clinician = self.login(client, "clinic.clinician")
                self.assertEqual(getattr(client, method)(path, headers=clinician,
                                                        **kwargs).status_code, 403)
            robin = self.login(client, "robin.portal")
            for path, method in (
                ("/worklists/appointment-change-requests", "get"),
                ("/appointment-change-requests/1/review", "post"),
            ):
                self.assertEqual(getattr(client, method)(path, headers=robin).status_code, 403)
            response = client.post(
                "/portal/appointment-change-requests?secret=do-not-audit",
                json={"appointment_id": self.first_appointment, "kind": "cancel"},
                headers=robin,
            )
            self.assertEqual(response.status_code, 201)
        with Session(self.engine) as session:
            events = session.scalars(select(AuditEvent)).all()
            self.assertTrue(any(event.route_template ==
                                "/portal/appointment-change-requests"
                                and event.event_type == "clinical_write" for event in events))
            self.assertNotIn("do-not-audit", repr(events))
            self.assertNotIn("Synthetic test password!", repr(events))


if __name__ == "__main__":
    unittest.main()
