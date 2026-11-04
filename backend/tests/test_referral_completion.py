"""Referral follow-up is recorded without rewriting the referring note."""

import unittest
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Base, Encounter, Patient
from backend.referrals import (
    cancel_referral,
    complete_referral,
    create_referral,
    list_referrals,
)
from backend.schemas import (
    ReferralCancel,
    ReferralComplete,
    ReferralCreate,
    ReferralRead,
)

VISIT_DATE = date(2026, 10, 20)


class ReferralCompletionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Avery", last_name="Example",
                date_of_birth=date(1989, 3, 15), sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            note = Encounter(
                patient_id=patient.id, visit_date=VISIT_DATE,
                reason_for_visit="Synthetic consultation",
                assessment="Fictional assessment",
            )
            session.add(note)
            session.flush()
            self.encounter_id = note.id
            referral = create_referral(
                session, note.id,
                ReferralCreate(
                    specialty="Fictional orthopedics",
                    reason="Review a synthetic finding", priority="urgent",
                ),
            )
            session.flush()
            self.referral_id = referral.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_completion_preserves_original_request_and_is_listed(self):
        with Session(self.engine) as session:
            completed = complete_referral(
                session, self.referral_id,
                ReferralComplete(
                    seen_on=VISIT_DATE,
                    follow_up_summary="  Synthetic specialist advice recorded.  ",
                ),
            )
            session.commit()
            saved = ReferralRead.model_validate(completed)
            self.assertEqual(saved.status, "completed")
            self.assertEqual(saved.seen_on, VISIT_DATE)
            self.assertEqual(
                saved.follow_up_summary, "Synthetic specialist advice recorded."
            )
            self.assertIsNotNone(saved.completed_at)
            self.assertEqual(saved.specialty, "Fictional orthopedics")
            self.assertEqual(saved.reason, "Review a synthetic finding")
            self.assertEqual(saved.priority, "urgent")
            self.assertIsNone(saved.cancellation_reason)

        with Session(self.engine) as session:
            self.assertEqual(
                list_referrals(session, self.encounter_id)[0].status, "completed"
            )

    def test_completion_after_note_finalization_leaves_signed_note_unchanged(self):
        with Session(self.engine) as session:
            note = session.get(Encounter, self.encounter_id)
            note.finalized_at = datetime.now(timezone.utc)
            session.commit()

        with Session(self.engine) as session:
            complete_referral(
                session, self.referral_id,
                ReferralComplete(
                    seen_on=VISIT_DATE,
                    follow_up_summary="Synthetic follow-up after signing",
                ),
            )
            session.commit()
            note = session.get(Encounter, self.encounter_id)
            self.assertEqual(note.assessment, "Fictional assessment")
            self.assertIsNotNone(note.finalized_at)

    def test_repeat_completion_and_cancellation_are_rejected(self):
        with Session(self.engine) as session:
            complete_referral(
                session, self.referral_id,
                ReferralComplete(
                    seen_on=VISIT_DATE, follow_up_summary="Original summary",
                ),
            )
            session.commit()

        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                complete_referral(
                    session, self.referral_id,
                    ReferralComplete(
                        seen_on=VISIT_DATE, follow_up_summary="Replacement",
                    ),
                )
            self.assertEqual(raised.exception.status_code, 409)
            with self.assertRaises(HTTPException) as raised:
                cancel_referral(
                    session, self.referral_id,
                    ReferralCancel(reason="Not needed"),
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(
                list_referrals(session, self.encounter_id)[0].follow_up_summary,
                "Original summary",
            )

    def test_cancelled_referral_cannot_be_completed(self):
        with Session(self.engine) as session:
            cancel_referral(
                session, self.referral_id,
                ReferralCancel(reason="Patient declined"),
            )
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                complete_referral(
                    session, self.referral_id,
                    ReferralComplete(
                        seen_on=VISIT_DATE, follow_up_summary="Not seen",
                    ),
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(list_referrals(session, self.encounter_id)[0].status,
                             "cancelled")

    def test_date_before_referring_visit_rejected_without_status_change(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                complete_referral(
                    session, self.referral_id,
                    ReferralComplete(
                        seen_on=VISIT_DATE - timedelta(days=1),
                        follow_up_summary="Impossible follow-up",
                    ),
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(
                list_referrals(session, self.encounter_id)[0].status, "requested"
            )

    def test_missing_request_returns_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                complete_referral(
                    session, 99999,
                    ReferralComplete(
                        seen_on=VISIT_DATE, follow_up_summary="Not found",
                    ),
                )
            self.assertEqual(raised.exception.status_code, 404)

    def test_completion_payload_requires_valid_date_and_summary(self):
        for summary in ("", "  ", "x" * 4001):
            with self.assertRaises(ValidationError):
                ReferralComplete(seen_on=VISIT_DATE, follow_up_summary=summary)
        with self.assertRaises(ValidationError):
            ReferralComplete(
                seen_on=date.today() + timedelta(days=1),
                follow_up_summary="Fictional",
            )
        with self.assertRaises(ValidationError):
            ReferralComplete.model_validate({
                "seen_on": VISIT_DATE,
                "follow_up_summary": "Fictional",
                "status": "completed",
            })


if __name__ == "__main__":
    unittest.main()
