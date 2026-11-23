"""Admin-only, cursor-paginated review of synthetic audit metadata."""

import csv
from io import StringIO
import unittest
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.audit import record_audit_event
from backend.main import app
from backend.models import AuditEvent, Base, Patient


class AuditReviewTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Demo", last_name="Patient",
                date_of_birth=date(1990, 1, 1), sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            self.patient_id = patient.id
            for username, kind, role, patient_id in (
                ("demo.admin", "staff", "admin", None),
                ("demo.clinician", "staff", "clinician", None),
                ("demo.desk", "staff", "front_desk", None),
                ("demo.patient", "patient", None, patient.id),
            ):
                create_user_account(
                    session, username=username, password="Synthetic audit password!",
                    account_type=kind, staff_role=role, patient_id=patient_id,
                )
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def login(self, client, username):
        response = client.post("/auth/login", json={
            "username": username, "password": "Synthetic audit password!",
        })
        self.assertEqual(response.status_code, 200)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_review_requires_admin_and_denials_are_audited(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            anonymous = client.get("/admin/audit-events")
            clinician = self.login(client, "demo.clinician")
            desk = self.login(client, "demo.desk")
            patient = self.login(client, "demo.patient")
            for headers in (clinician, desk, patient):
                with self.subTest(headers=headers["Authorization"][:12]):
                    denied = client.get("/admin/audit-events", headers=headers)
                    self.assertEqual(denied.status_code, 403)
                    self.assertEqual(denied.headers["cache-control"], "no-store")
                    self.assertNotIn("occurred_at", denied.text)
            self.assertEqual(anonymous.status_code, 401)
            self.assertEqual(anonymous.headers["cache-control"], "no-store")

            admin = self.login(client, "demo.admin")
            allowed = client.get("/admin/audit-events", headers=admin)
            self.assertEqual(allowed.status_code, 200)

        with Session(self.engine) as session:
            denials = session.scalars(
                select(AuditEvent)
                .where(AuditEvent.route_template == "/admin/audit-events")
                .where(AuditEvent.status_code.in_([401, 403]))
            ).all()
            self.assertEqual(len(denials), 4)
            self.assertEqual(
                sorted(event.status_code for event in denials), [401, 403, 403, 403],
            )
            self.assertTrue(all(e.event_type == "access_denied" for e in denials))
            self.assertTrue(all(e.subject_patient_id is None for e in denials[:3]) or
                            any(e.subject_patient_id == self.patient_id for e in denials))

    def test_bounded_newest_first_cursor_and_safe_response_fields(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            admin = self.login(client, "demo.admin")
            with Session(self.engine) as session:
                record_audit_event(
                    session, event_type="clinical_read",
                    route_template="/patients/{patient_id}", http_method="GET",
                    status_code=200, actor_user_id=1,
                    subject_patient_id=self.patient_id,
                    resource_id=self.patient_id,
                )
                session.flush()
                older_id = session.scalars(
                    select(AuditEvent.id).where(AuditEvent.event_type == "clinical_read")
                ).one()
                record_audit_event(
                    session, event_type="access_denied",
                    route_template="/patients/{patient_id}", http_method="GET",
                    status_code=403, subject_patient_id=self.patient_id,
                    resource_id=self.patient_id,
                )
                session.flush()
                newer_id = session.scalars(
                    select(AuditEvent.id).where(AuditEvent.event_type == "access_denied")
                ).one()
                session.commit()

            first = client.get("/admin/audit-events?limit=2&private=never-store", headers=admin)
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.headers["cache-control"], "no-store")
            self.assertEqual([e["id"] for e in first.json()], [newer_id, older_id])
            self.assertEqual(set(first.json()[0]), {
                "id", "occurred_at", "event_type", "route_template", "http_method",
                "status_code", "actor_user_id", "subject_patient_id", "resource_id",
            })
            self.assertEqual(first.json()[0]["route_template"], "/patients/{patient_id}")
            self.assertEqual(first.json()[0]["subject_patient_id"], self.patient_id)

            # Reviewing the log writes a newer event; the cursor must not repeat it.
            second = client.get(
                f"/admin/audit-events?limit=2&before_id={older_id}", headers=admin,
            )
            self.assertEqual(second.status_code, 200)
            self.assertTrue(all(e["id"] < older_id for e in second.json()))
            filtered = client.get(
                "/admin/audit-events?event_type=access_denied", headers=admin,
            )
            self.assertEqual(filtered.status_code, 200)
            self.assertTrue(all(e["event_type"] == "access_denied" for e in filtered.json()))

            for parameters in ("limit=0", "limit=101", "before_id=0",
                               "event_type=invalid"):
                with self.subTest(parameters=parameters):
                    self.assertEqual(
                        client.get(f"/admin/audit-events?{parameters}", headers=admin)
                        .status_code, 422,
                    )

        with Session(self.engine) as session:
            reviews = session.scalars(
                select(AuditEvent)
                .where(AuditEvent.route_template == "/admin/audit-events")
            ).all()
            self.assertGreaterEqual(len(reviews), 4)
            self.assertTrue(all(e.resource_id is None for e in reviews))
            self.assertNotIn("never-store", repr(reviews))
            self.assertNotIn("Synthetic audit password!", first.text)
            self.assertNotIn(admin["Authorization"], first.text)


    def test_csv_export_is_admin_only_paged_and_audited(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            admin = self.login(client, "demo.admin")
            with Session(self.engine) as session:
                for route in ("/patients/{patient_id}", "/patients/{patient_id}/timeline"):
                    record_audit_event(
                        session, event_type="clinical_read", route_template=route,
                        http_method="GET", status_code=200,
                        subject_patient_id=self.patient_id,
                    )
                    session.flush()
                ids = session.scalars(
                    select(AuditEvent.id)
                    .where(AuditEvent.event_type == "clinical_read")
                    .order_by(AuditEvent.id)
                ).all()
                session.commit()

            first = client.get(
                "/admin/audit-events/export?limit=1&event_type=clinical_read&secret=do-not-store",
                headers=admin,
            )
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.headers["cache-control"], "no-store")
            self.assertTrue(first.headers["content-type"].startswith("text/csv"))
            self.assertEqual(first.headers["x-content-type-options"], "nosniff")
            self.assertEqual(
                first.headers["content-disposition"],
                'attachment; filename="audit-events.csv"',
            )
            rows = list(csv.DictReader(StringIO(first.text)))
            self.assertEqual(len(rows), 1)
            self.assertEqual(int(rows[0]["id"]), ids[-1])
            self.assertEqual(rows[0]["subject_patient_id"], str(self.patient_id))
            self.assertEqual(rows[0]["actor_user_id"], "")
            self.assertEqual(set(rows[0]), {
                "id", "occurred_at", "event_type", "route_template", "http_method",
                "status_code", "actor_user_id", "subject_patient_id", "resource_id",
            })
            self.assertNotIn("secret", first.text)
            self.assertNotIn("Synthetic audit password!", first.text)

            second = client.get(
                f"/admin/audit-events/export?before_id={ids[-1]}&limit=1"
                "&event_type=clinical_read", headers=admin,
            )
            self.assertEqual(second.status_code, 200)
            self.assertEqual(
                int(list(csv.DictReader(StringIO(second.text)))[0]["id"]), ids[0],
            )
            for parameters in ("limit=0", "limit=101", "before_id=0",
                               "event_type=other"):
                with self.subTest(parameters=parameters):
                    self.assertEqual(client.get(
                        f"/admin/audit-events/export?{parameters}", headers=admin,
                    ).status_code, 422)

            for username in ("demo.clinician", "demo.desk", "demo.patient"):
                forbidden = client.get(
                    "/admin/audit-events/export", headers=self.login(client, username),
                )
                self.assertEqual(forbidden.status_code, 403)
                self.assertEqual(forbidden.headers["cache-control"], "no-store")
                self.assertNotIn("id,occurred_at", forbidden.text)
            anonymous = client.get("/admin/audit-events/export")
            self.assertEqual(anonymous.status_code, 401)
            self.assertEqual(anonymous.headers["cache-control"], "no-store")

        with Session(self.engine) as session:
            exports = session.scalars(
                select(AuditEvent)
                .where(AuditEvent.route_template == "/admin/audit-events/export")
                .order_by(AuditEvent.id)
            ).all()
            self.assertGreaterEqual(len(exports), 6)
            self.assertEqual([event.status_code for event in exports[:2]], [200, 200])
            self.assertTrue(all(event.resource_id is None for event in exports))
            self.assertNotIn("do-not-store", repr(exports))


if __name__ == "__main__":
    unittest.main()
