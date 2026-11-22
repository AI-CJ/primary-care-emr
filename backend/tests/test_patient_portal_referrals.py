"""Authenticated patient access to referral summaries."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.account_auth import create_user_account
from backend.main import app
from backend.models import Base, Encounter, Patient, Referral, UserAccount, UserSession


class PatientPortalReferralTests(unittest.TestCase):
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
                    reason_for_visit="Private finalized visit", finalized_at=finalized,
                ),
                Encounter(
                    patient_id=self.patient_id, visit_date=date(2026, 11, 6),
                    reason_for_visit="Unfinished visit",
                ),
                Encounter(
                    patient_id=self.other_id, visit_date=date(2026, 11, 7),
                    reason_for_visit="Other patient visit", finalized_at=finalized,
                ),
            ]
            session.add_all(visits)
            session.flush()
            start = datetime(2026, 11, 5, 9, tzinfo=timezone.utc)
            session.add_all([
                Referral(
                    encounter_id=visits[0].id, specialty="Older fictional referral",
                    reason="Private clinical reason", priority="routine",
                    status="requested", requested_at=start,
                ),
                Referral(
                    encounter_id=visits[0].id, specialty="Completed fictional referral",
                    reason="Private completed reason", priority="urgent",
                    status="completed", requested_at=start + timedelta(minutes=1),
                    seen_on=date(2026, 11, 7),
                    follow_up_summary="Staff-only follow-up",
                ),
                Referral(
                    encounter_id=visits[0].id, specialty="Cancelled fictional referral",
                    reason="Private cancellation context", priority="routine",
                    status="cancelled", requested_at=start + timedelta(minutes=2),
                    cancelled_at=start + timedelta(hours=1),
                    cancellation_reason="Staff-only cancellation reason",
                ),
                Referral(
                    encounter_id=visits[0].id, specialty="Recent fictional referral",
                    reason="Private recent context", priority="urgent",
                    status="requested", requested_at=start + timedelta(minutes=3),
                ),
                Referral(
                    encounter_id=visits[1].id, specialty="Unreleased draft referral",
                    reason="Private draft reason", priority="urgent",
                    status="requested", requested_at=start + timedelta(days=1),
                ),
                Referral(
                    encounter_id=visits[2].id, specialty="Other patient referral",
                    reason="Private other patient context", priority="urgent",
                    status="requested", requested_at=start + timedelta(days=2),
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

    def test_only_own_recent_finalized_referrals_and_safe_fields(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            morgan = self.login(client, "morgan.portal")
            taylor = self.login(client, "taylor.portal")

            response = client.get("/portal/referrals", headers=avery)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(
                [row["specialty"] for row in response.json()],
                [
                    "Recent fictional referral", "Cancelled fictional referral",
                    "Completed fictional referral",
                ],
            )
            self.assertEqual(
                [row["status"] for row in response.json()],
                ["requested", "cancelled", "completed"],
            )
            self.assertEqual(response.json()[2]["seen_on"], "2026-11-07")
            self.assertEqual(set(response.json()[0]), {
                "id", "specialty", "priority", "status", "visit_date", "seen_on",
            })
            for private in (
                "patient_id", "encounter_id", "reason", "cancellation_reason",
                "follow_up_summary", "Private", "Staff-only",
                "Unreleased draft referral", "Other patient referral",
                "Older fictional referral",
            ):
                self.assertNotIn(private, response.text)

            other = client.get("/portal/referrals", headers=morgan)
            self.assertEqual(other.status_code, 200)
            self.assertEqual(
                [row["specialty"] for row in other.json()], ["Other patient referral"],
            )
            self.assertEqual(client.get("/portal/referrals", headers=taylor).json(), [])

            override = client.get(
                f"/portal/referrals?patient_id={self.other_id}", headers=avery,
            )
            self.assertEqual(override.status_code, 200)
            self.assertEqual(override.json(), response.json())

    def test_staff_boundary_and_read_only_access(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            missing = client.get("/portal/referrals")
            self.assertEqual(missing.status_code, 401)
            self.assertEqual(missing.headers["www-authenticate"], "Bearer")
            self.assertEqual(client.get(
                "/portal/referrals", headers={"Authorization": "Bearer invalid"},
            ).status_code, 401)

            staff = self.login(client, "clinic.staff", "Fictional staff password!")
            self.assertEqual(client.get("/portal/referrals", headers=staff).status_code, 403)
            self.assertEqual(client.get(
                f"/patients/{self.patient_id}/portal-preview/referrals",
                headers=staff,
            ).status_code, 200)

            avery = self.login(client, "avery.portal")
            for path in (
                "/patients",
                f"/patients/{self.other_id}/referrals",
                f"/patients/{self.other_id}/portal-preview/referrals",
                "/portal/referrals/1",
            ):
                with self.subTest(path=path):
                    self.assertEqual(client.get(path, headers=avery).status_code, 403)
            self.assertEqual(client.post(
                "/portal/referrals", headers=avery,
                json={"specialty": "Not permitted"},
            ).status_code, 403)

    def test_revoked_expired_and_disabled_sessions(self):
        with patch("backend.main.engine", self.engine), TestClient(app) as client:
            avery = self.login(client, "avery.portal")
            self.assertEqual(client.get("/portal/referrals", headers=avery).status_code, 200)
            self.assertEqual(client.post("/auth/logout", headers=avery).status_code, 204)
            self.assertEqual(client.get("/portal/referrals", headers=avery).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                session.query(UserSession).filter_by(revoked_at=None).one().expires_at = (
                    datetime.now(timezone.utc) - timedelta(seconds=1)
                )
                session.commit()
            self.assertEqual(client.get("/portal/referrals", headers=avery).status_code, 401)

            avery = self.login(client, "avery.portal")
            with Session(self.engine) as session:
                session.query(UserAccount).filter_by(
                    username="avery.portal",
                ).one().is_active = False
                session.commit()
            self.assertEqual(client.get("/portal/referrals", headers=avery).status_code, 401)


if __name__ == "__main__":
    unittest.main()
