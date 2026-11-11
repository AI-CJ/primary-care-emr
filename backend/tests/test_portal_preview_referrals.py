"""Portal referral summaries keep draft and staff-only details out of the preview."""

import unittest
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Base, Encounter, Patient, Referral
from backend.referrals import list_portal_preview_referrals


class PortalPreviewReferralTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            patient = Patient(
                first_name="Avery", last_name="Example",
                date_of_birth=date(1990, 3, 17), sex_at_birth="unknown",
            )
            other = Patient(
                first_name="Morgan", last_name="Sample",
                date_of_birth=date(1988, 6, 12), sex_at_birth="unknown",
            )
            empty = Patient(
                first_name="Taylor", last_name="Test",
                date_of_birth=date(1995, 4, 19), sex_at_birth="unknown",
            )
            session.add_all([patient, other, empty])
            session.flush()
            self.patient_id = patient.id
            self.empty_id = empty.id

            final_at = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
            older = Encounter(
                patient_id=patient.id, visit_date=date(2026, 10, 28),
                reason_for_visit="Private synthetic visit", finalized_at=final_at,
            )
            recent = Encounter(
                patient_id=patient.id, visit_date=date(2026, 11, 5),
                reason_for_visit="Other private synthetic visit", finalized_at=final_at,
            )
            draft = Encounter(
                patient_id=patient.id, visit_date=date(2026, 11, 7),
                reason_for_visit="Unfinished synthetic visit",
            )
            other_visit = Encounter(
                patient_id=other.id, visit_date=date(2026, 11, 9),
                reason_for_visit="Another patient's visit", finalized_at=final_at,
            )
            session.add_all([older, recent, draft, other_visit])
            session.flush()

            base = datetime(2026, 11, 5, 9, tzinfo=timezone.utc)
            referrals = [
                Referral(
                    encounter_id=older.id, specialty="Fictional dermatology",
                    reason="Private synthetic dermatology reason",
                    priority="routine", status="requested",
                    requested_at=base,
                ),
                Referral(
                    encounter_id=recent.id, specialty="Fictional orthopedics",
                    reason="Private synthetic orthopedics reason",
                    priority="urgent", status="completed",
                    requested_at=base + timedelta(minutes=1),
                    seen_on=date(2026, 11, 6),
                    follow_up_summary="Private synthetic specialist narrative",
                ),
                Referral(
                    encounter_id=recent.id, specialty="Fictional cardiology",
                    reason="Private synthetic cardiology reason",
                    priority="routine", status="cancelled",
                    requested_at=base + timedelta(minutes=1),
                    cancellation_reason="Private synthetic cancellation reason",
                    cancelled_at=base + timedelta(hours=1),
                ),
                Referral(
                    encounter_id=older.id, specialty="Fictional radiology",
                    reason="Private synthetic imaging reason",
                    priority="routine", status="requested",
                    requested_at=base + timedelta(minutes=2),
                ),
                Referral(
                    encounter_id=draft.id, specialty="Unreleased draft referral",
                    reason="Private unfinished reason", priority="urgent",
                    status="requested", requested_at=base + timedelta(days=1),
                ),
                Referral(
                    encounter_id=other_visit.id, specialty="Other patient referral",
                    reason="Private other patient reason", priority="urgent",
                    status="requested", requested_at=base + timedelta(days=2),
                ),
            ]
            session.add_all(referrals)
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_only_three_recent_finalized_referrals_for_patient(self):
        with Session(self.engine) as session:
            summaries = list_portal_preview_referrals(session, self.patient_id)

        self.assertEqual(
            [item.specialty for item in summaries],
            ["Fictional radiology", "Fictional cardiology", "Fictional orthopedics"],
        )
        self.assertEqual([item.status for item in summaries],
                         ["requested", "cancelled", "completed"])
        self.assertEqual(summaries[1].visit_date, date(2026, 11, 5))
        self.assertEqual(summaries[2].seen_on, date(2026, 11, 6))

    def test_response_excludes_staff_only_text(self):
        with Session(self.engine) as session:
            summaries = list_portal_preview_referrals(session, self.patient_id)

        allowed = {"id", "specialty", "priority", "status", "visit_date", "seen_on"}
        for summary in summaries:
            self.assertEqual(set(summary.model_dump(mode="json")), allowed)
        for hidden in (
            "Private synthetic", "Unreleased draft referral", "Other patient referral"
        ):
            self.assertNotIn(hidden, repr(summaries))

    def test_empty_chart_and_missing_patient(self):
        with Session(self.engine) as session:
            self.assertEqual(list_portal_preview_referrals(session, self.empty_id), [])
            with self.assertRaises(HTTPException) as raised:
                list_portal_preview_referrals(session, 99999)
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
