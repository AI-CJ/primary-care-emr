"""Authenticated patient access to released lab information."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import (
    Base, Encounter, LabOrder, LabResult, Patient, UserAccount, UserSession,
)


class PatientPortalLabOrderTests(unittest.TestCase):
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
            finalized = datetime(2026, 11, 8, tzinfo=timezone.utc)
            visits = [
                Encounter(
                    patient_id=self.patient_id, visit_date=date(2026, 11, 5),
                    reason_for_visit="Synthetic completed visit", finalized_at=finalized,
                ),
                Encounter(
                    patient_id=self.patient_id, visit_date=date(2026, 11, 6),
                    reason_for_visit="Private draft visit",
                ),
                Encounter(
                    patient_id=self.other_id, visit_date=date(2026, 11, 7),
                    reason_for_visit="Other patient's visit", finalized_at=finalized,
                ),
            ]
            session.add_all(visits)
            session.flush()
            base = datetime(2026, 11, 5, 9, tzinfo=timezone.utc)
            orders = [
                LabOrder(
                    encounter_id=visits[0].id, test_name="Released fictional CBC",
                    priority="routine", status="resulted", ordered_at=base,
                    clinical_reason="Private clinical reason",
                ),
                LabOrder(
                    encounter_id=visits[0].id, test_name="Withheld fictional panel",
                    priority="urgent", status="resulted",
                    ordered_at=base + timedelta(minutes=1),
                ),
                LabOrder(
                    encounter_id=visits[0].id, test_name="Pending fictional test",
                    priority="routine", status="ordered",
                    ordered_at=base + timedelta(minutes=2),
                ),
                LabOrder(
                    encounter_id=visits[0].id, test_name="Cancelled fictional test",
                    priority="routine", status="cancelled",
                    ordered_at=base + timedelta(minutes=3),
                    cancelled_at=base + timedelta(hours=1),
                    cancellation_reason="Private cancellation reason",
                ),
                LabOrder(
                    encounter_id=visits[1].id, test_name="Draft-only fictional test",
                    priority="routine", status="ordered",
                    ordered_at=base + timedelta(days=1),
                ),
                LabOrder(
                    encounter_id=visits[2].id, test_name="Another patient test",
                    priority="routine", status="resulted",
                    ordered_at=base + timedelta(days=2),
                ),
            ]
            session.add_all(orders)
            session.flush()
            session.add_all([
                LabResult(
                    lab_order_id=orders[0].id,
                    collected_on=date(2026, 11, 5),
                    result_text="Fictional released result",
                    reported_at=base + timedelta(days=1),
                    released_at=finalized,
                ),
                LabResult(
                    lab_order_id=orders[1].id,
                    collected_on=date(2026, 11, 5),
                    result_text="Confidential unreleased result",
                    reported_at=base + timedelta(days=1),
                ),
                LabResult(
                    lab_order_id=orders[5].id,
                    collected_on=date(2026, 11, 7),
                    result_text="Other patient's result",
                    reported_at=base + timedelta(days=3),
                    released_at=finalized,
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

    def test_own_finalized_orders_and_only_released_results(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            morgan = self.login(client, "morgan.portal")
            taylor = self.login(client, "taylor.portal")

            response = client.get("/portal/lab-orders", headers=avery)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            orders = response.json()
            self.assertEqual(
                [item["test_name"] for item in orders],
                [
                    "Cancelled fictional test", "Pending fictional test",
                    "Withheld fictional panel", "Released fictional CBC",
                ],
            )
            self.assertEqual(
                [item["status"] for item in orders],
                ["cancelled", "ordered", "resulted", "resulted"],
            )
            self.assertIsNone(orders[0]["result"])
            self.assertIsNone(orders[1]["result"])
            self.assertIsNone(orders[2]["result"])
            self.assertEqual(
                orders[3]["result"]["result_text"], "Fictional released result",
            )
            self.assertEqual(set(orders[0]), {
                "id", "test_name", "status", "ordered_at", "cancelled_at", "result",
            })
            self.assertEqual(set(orders[3]["result"]), {
                "collected_on", "result_text", "reported_at",
            })
            for private in (
                "patient_id", "encounter_id", "clinical_reason", "cancellation_reason",
                "priority", "released_at", "Private clinical reason",
                "Private cancellation reason", "Confidential unreleased result",
                "Draft-only fictional test", "Another patient test",
            ):
                self.assertNotIn(private, response.text)
            other = client.get("/portal/lab-orders", headers=morgan)
            self.assertEqual(other.status_code, 200)
            self.assertEqual(
                [row["test_name"] for row in other.json()], ["Another patient test"],
            )
            self.assertEqual(client.get(
                "/portal/lab-orders", headers=taylor,
            ).json(), [])
            override = client.get(
                f"/portal/lab-orders?patient_id={self.other_id}", headers=avery,
            )
            self.assertEqual(override.status_code, 200)
            self.assertEqual(override.json(), orders)

    def test_staff_boundary_and_read_only_access(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            missing = client.get("/portal/lab-orders")
            self.assertEqual(missing.status_code, 401)
            self.assertEqual(missing.headers["www-authenticate"], "Bearer")
            self.assertEqual(client.get(
                "/portal/lab-orders",
                headers={"Authorization": "Bearer invalid"},
            ).status_code, 401)
            staff = self.login(client, "clinic.staff", "Fictional staff password!")
            self.assertEqual(
                client.get("/portal/lab-orders", headers=staff).status_code, 403,
            )
            self.assertEqual(client.get(
                f"/patients/{self.patient_id}/portal-preview/lab-orders",
                headers=staff,
            ).status_code, 200)
            avery = self.login(client, "avery.portal")
            for path in (
                "/patients",
                f"/patients/{self.other_id}/lab-orders",
                f"/patients/{self.other_id}/portal-preview/lab-orders",
                "/portal/lab-orders/1",
            ):
                with self.subTest(path=path):
                    self.assertEqual(client.get(path, headers=avery).status_code, 403)
            self.assertEqual(client.post(
                "/portal/lab-orders", headers=avery,
                json={"test_name": "Not allowed"},
            ).status_code, 403)

    def test_revoked_expired_and_disabled_sessions(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            self.assertEqual(client.get(
                "/portal/lab-orders", headers=avery,
            ).status_code, 200)
            self.assertEqual(client.post("/auth/logout", headers=avery).status_code, 204)
            self.assertEqual(client.get(
                "/portal/lab-orders", headers=avery,
            ).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                record = session.query(UserSession).filter_by(revoked_at=None).one()
                record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                session.commit()
            self.assertEqual(client.get(
                "/portal/lab-orders", headers=avery,
            ).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                session.query(UserAccount).filter_by(
                    username="avery.portal",
                ).one().is_active = False
                session.commit()
            self.assertEqual(client.get(
                "/portal/lab-orders", headers=avery,
            ).status_code, 401)


if __name__ == "__main__":
    unittest.main()
