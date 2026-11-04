"""Cancelled specialist referrals retain their original clinical context."""

import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Base, Encounter, Patient
from backend.referrals import cancel_referral, create_referral, list_referrals
from backend.schemas import ReferralCancel, ReferralCreate, ReferralRead


class ReferralCancellationTests(unittest.TestCase):
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
            draft = Encounter(
                patient_id=patient.id, visit_date=date(2026, 11, 2),
                reason_for_visit="Synthetic consultation",
            )
            session.add(draft)
            session.flush()
            self.encounter_id = draft.id
            referral = create_referral(session, draft.id, ReferralCreate(
                specialty="Fictional dermatology",
                reason="Synthetic follow-up",
                priority="urgent",
            ))
            session.flush()
            self.referral_id = referral.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_cancel_preserves_request_details_and_reason(self):
        with Session(self.engine) as session:
            cancelled = cancel_referral(
                session, self.referral_id,
                ReferralCancel(reason="  Duplicate referral request  "),
            )
            session.commit()
            data = ReferralRead.model_validate(cancelled)
            self.assertEqual(data.status, "cancelled")
            self.assertEqual(data.cancellation_reason, "Duplicate referral request")
            self.assertIsNotNone(data.cancelled_at)
            self.assertEqual(data.specialty, "Fictional dermatology")
            self.assertEqual(data.priority, "urgent")
            self.assertEqual(data.reason, "Synthetic follow-up")

        with Session(self.engine) as session:
            records = list_referrals(session, self.encounter_id)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].status, "cancelled")
            self.assertEqual(records[0].cancellation_reason, "Duplicate referral request")

    def test_cannot_cancel_twice_or_overwrite_cancellation_reason(self):
        with Session(self.engine) as session:
            cancel_referral(session, self.referral_id, ReferralCancel(reason="Not needed"))
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                cancel_referral(
                    session, self.referral_id, ReferralCancel(reason="Different reason")
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(
                list_referrals(session, self.encounter_id)[0].cancellation_reason,
                "Not needed",
            )

    def test_pending_referral_can_be_cancelled_after_note_finalization(self):
        with Session(self.engine) as session:
            note = session.get(Encounter, self.encounter_id)
            note.assessment = "Final signed assessment"
            note.finalized_at = datetime.now(timezone.utc)
            session.commit()

        with Session(self.engine) as session:
            cancelled = cancel_referral(
                session, self.referral_id,
                ReferralCancel(reason="Patient declined specialist follow-up"),
            )
            session.commit()
            self.assertEqual(cancelled.status, "cancelled")
            note = session.get(Encounter, self.encounter_id)
            self.assertEqual(note.assessment, "Final signed assessment")
            self.assertIsNotNone(note.finalized_at)

    def test_missing_referral_returns_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                cancel_referral(session, 9999, ReferralCancel(reason="Not found"))
            self.assertEqual(raised.exception.status_code, 404)

    def test_cancellation_requires_a_reason_and_rejects_extra_fields(self):
        for reason in ("", "  ", "x" * 1001):
            with self.assertRaises(ValidationError):
                ReferralCancel(reason=reason)
        with self.assertRaises(ValidationError):
            ReferralCancel.model_validate({
                "reason": "Not needed", "status": "cancelled",
            })


if __name__ == "__main__":
    unittest.main()
