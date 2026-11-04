"""Referral requests remain associated with their original visit notes."""

import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Base, Encounter, Patient
from backend.referrals import create_referral, list_referrals
from backend.schemas import ReferralCreate, ReferralRead


class ReferralTests(unittest.TestCase):
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
                patient_id=patient.id,
                visit_date=date(2026, 11, 2),
                reason_for_visit="Synthetic checkup",
            )
            other = Encounter(
                patient_id=patient.id,
                visit_date=date(2026, 11, 1),
                reason_for_visit="Fictional follow-up",
            )
            final = Encounter(
                patient_id=patient.id,
                visit_date=date(2026, 10, 20),
                reason_for_visit="Synthetic consultation",
                finalized_at=datetime.now(timezone.utc),
            )
            session.add_all([draft, other, final])
            session.flush()
            self.draft_id = draft.id
            self.other_id = other.id
            self.final_id = final.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_create_and_list_referral_for_draft_visit(self):
        with Session(self.engine) as session:
            referral = create_referral(
                session,
                self.draft_id,
                ReferralCreate(
                    specialty="  Fictional cardiology  ",
                    reason="  Follow-up on synthetic findings  ",
                    priority="urgent",
                ),
            )
            session.commit()
            session.refresh(referral)
            saved = ReferralRead.model_validate(referral)
            self.assertEqual(saved.encounter_id, self.draft_id)
            self.assertEqual(saved.specialty, "Fictional cardiology")
            self.assertEqual(saved.reason, "Follow-up on synthetic findings")
            self.assertEqual(saved.priority, "urgent")
            self.assertEqual(saved.status, "requested")
            self.assertIsNotNone(saved.requested_at)

        with Session(self.engine) as session:
            self.assertEqual(len(list_referrals(session, self.draft_id)), 1)
            self.assertEqual(list_referrals(session, self.other_id), [])
            self.assertEqual(list_referrals(session, self.final_id), [])

    def test_multiple_referrals_preserve_order(self):
        with Session(self.engine) as session:
            create_referral(session, self.draft_id, ReferralCreate(
                specialty="Fictional dermatology", reason="Synthetic rash",
            ))
            create_referral(session, self.draft_id, ReferralCreate(
                specialty="Fictional pulmonology", reason="Synthetic follow-up",
            ))
            session.commit()
        with Session(self.engine) as session:
            saved = list_referrals(session, self.draft_id)
            self.assertEqual([item.specialty for item in saved], [
                "Fictional dermatology", "Fictional pulmonology",
            ])
            self.assertEqual([item.priority for item in saved], ["routine", "routine"])

    def test_finalized_note_rejects_new_referrals(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_referral(session, self.final_id, ReferralCreate(
                    specialty="Cardiology", reason="Synthetic example",
                ))
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(list_referrals(session, self.final_id), [])

    def test_missing_note_returns_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                create_referral(session, 9999, ReferralCreate(
                    specialty="Cardiology", reason="Synthetic example",
                ))
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                list_referrals(session, 9999)
            self.assertEqual(raised.exception.status_code, 404)

    def test_validation_rejects_blank_or_oversize_and_extra_fields(self):
        for specialty in ("", "  ", "X" * 201):
            with self.assertRaises(ValidationError):
                ReferralCreate(specialty=specialty, reason="Synthetic example")
        for reason in ("", "  ", "x" * 1001):
            with self.assertRaises(ValidationError):
                ReferralCreate(specialty="Cardiology", reason=reason)
        with self.assertRaises(ValidationError):
            ReferralCreate(specialty="Cardiology", reason="Test", priority="stat")
        with self.assertRaises(ValidationError):
            ReferralCreate.model_validate({
                "specialty": "Cardiology", "reason": "Test", "status": "sent",
            })


if __name__ == "__main__":
    unittest.main()
