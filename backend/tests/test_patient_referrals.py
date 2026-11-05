"""A patient referral list includes requests from all of their visits."""

import unittest
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Base, Encounter, Patient
from backend.referrals import (
    cancel_referral,
    complete_referral,
    create_referral,
    list_patient_referrals,
)
from backend.schemas import (
    PatientReferralRead,
    ReferralCancel,
    ReferralComplete,
    ReferralCreate,
    ReferralRead,
)


class PatientReferralHistoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Morgan", last_name="Example",
                date_of_birth=date(1988, 5, 12), sex_at_birth="unknown",
            )
            another = Patient(
                first_name="Casey", last_name="Test",
                date_of_birth=date(1990, 3, 8), sex_at_birth="unknown",
            )
            empty = Patient(
                first_name="Taylor", last_name="Sample",
                date_of_birth=date(1999, 8, 14), sex_at_birth="unknown",
            )
            session.add_all([patient, another, empty])
            session.flush()
            self.patient_id = patient.id
            self.another_patient_id = another.id
            self.empty_patient_id = empty.id
            old_visit = Encounter(
                patient_id=patient.id, visit_date=date(2026, 10, 20),
                reason_for_visit="Fictional consultation",
            )
            recent_visit = Encounter(
                patient_id=patient.id, visit_date=date(2026, 11, 2),
                reason_for_visit="Synthetic follow-up",
            )
            another_visit = Encounter(
                patient_id=another.id, visit_date=date(2026, 11, 3),
                reason_for_visit="Unrelated fictional patient",
            )
            session.add_all([old_visit, recent_visit, another_visit])
            session.flush()
            self.old_visit_id = old_visit.id
            self.recent_visit_id = recent_visit.id
            self.another_visit_id = another_visit.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_lists_only_selected_patients_referrals_with_visit_dates(self):
        with Session(self.engine) as session:
            create_referral(session, self.old_visit_id, ReferralCreate(
                specialty="Fictional dermatology", reason="Synthetic rash",
            ))
            create_referral(session, self.recent_visit_id, ReferralCreate(
                specialty="Fictional cardiology", reason="Synthetic review",
                priority="urgent",
            ))
            create_referral(session, self.another_visit_id, ReferralCreate(
                specialty="Fictional neurology", reason="Other chart",
            ))
            session.commit()
            rows = list_patient_referrals(session, self.patient_id)
            self.assertEqual(
                [referral.specialty for referral, _ in rows],
                ["Fictional cardiology", "Fictional dermatology"],
            )
            self.assertEqual(
                [visit_date for _, visit_date in rows],
                [date(2026, 11, 2), date(2026, 10, 20)],
            )
            self.assertEqual(
                list_patient_referrals(session, self.another_patient_id)[0][0].specialty,
                "Fictional neurology",
            )

    def test_completed_and_cancelled_requests_keep_their_history(self):
        with Session(self.engine) as session:
            completed = create_referral(
                session, self.old_visit_id,
                ReferralCreate(specialty="Fictional cardiology", reason="Review"),
            )
            cancelled = create_referral(
                session, self.recent_visit_id,
                ReferralCreate(specialty="Fictional dermatology", reason="Consult"),
            )
            session.flush()
            old_visit = session.get(Encounter, self.old_visit_id)
            old_visit.finalized_at = datetime.now(timezone.utc)
            complete_referral(
                session, completed.id,
                ReferralComplete(
                    seen_on=date(2026, 10, 21),
                    follow_up_summary="Fictional specialist follow-up",
                ),
            )
            cancel_referral(
                session, cancelled.id,
                ReferralCancel(reason="Patient declined fictional referral"),
            )
            session.commit()

        with Session(self.engine) as session:
            rows = list_patient_referrals(session, self.patient_id)
            chart = [
                PatientReferralRead(
                    **ReferralRead.model_validate(referral).model_dump(),
                    visit_date=visit_date,
                )
                for referral, visit_date in rows
            ]
            self.assertEqual([item.status for item in chart], ["cancelled", "completed"])
            self.assertEqual(
                chart[0].cancellation_reason, "Patient declined fictional referral"
            )
            self.assertEqual(chart[1].seen_on, date(2026, 10, 21))
            self.assertEqual(
                chart[1].follow_up_summary, "Fictional specialist follow-up"
            )
            self.assertIsNotNone(session.get(Encounter, self.old_visit_id).finalized_at)

    def test_same_visit_uses_latest_request_first(self):
        with Session(self.engine) as session:
            first = create_referral(
                session, self.recent_visit_id,
                ReferralCreate(specialty="Fictional radiology", reason="Imaging"),
            )
            second = create_referral(
                session, self.recent_visit_id,
                ReferralCreate(specialty="Fictional orthopedics", reason="Consult"),
            )
            base = datetime(2026, 11, 2, 14, tzinfo=timezone.utc)
            first.requested_at = base
            second.requested_at = base + timedelta(minutes=1)
            session.commit()
            self.assertEqual(
                [referral.id for referral, _ in
                 list_patient_referrals(session, self.patient_id)],
                [second.id, first.id],
            )

    def test_empty_chart_and_missing_patient(self):
        with Session(self.engine) as session:
            self.assertEqual(list_patient_referrals(session, self.empty_patient_id), [])
            with self.assertRaises(HTTPException) as raised:
                list_patient_referrals(session, 99999)
            self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
