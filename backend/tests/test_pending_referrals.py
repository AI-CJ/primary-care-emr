"""Outstanding referral requests remain visible until closed."""

import unittest
from datetime import date, datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Base, Encounter, Patient, Referral
from backend.referrals import (
    cancel_referral,
    complete_referral,
    create_referral,
    list_pending_referrals,
)
from backend.schemas import (
    PendingReferralRead,
    ReferralCancel,
    ReferralComplete,
    ReferralCreate,
    ReferralRead,
)


class PendingReferralTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            avery = Patient(
                first_name="Avery", last_name="Example",
                date_of_birth=date(1987, 4, 3), sex_at_birth="unknown",
            )
            morgan = Patient(
                first_name="Morgan", preferred_name="Mo", last_name="Sample",
                date_of_birth=date(1993, 2, 10), sex_at_birth="unknown",
            )
            session.add_all([avery, morgan])
            session.flush()
            first_visit = Encounter(
                patient_id=avery.id, visit_date=date(2026, 10, 20),
                reason_for_visit="Synthetic checkup",
                assessment="Fictional assessment",
            )
            second_visit = Encounter(
                patient_id=morgan.id, visit_date=date(2026, 10, 21),
                reason_for_visit="Synthetic follow-up",
                assessment="Fictional follow-up",
                finalized_at=datetime(2026, 10, 21, 15, tzinfo=timezone.utc),
            )
            session.add_all([first_visit, second_visit])
            session.flush()

            routine = Referral(
                encounter_id=first_visit.id, specialty="Fictional dermatology",
                reason="Synthetic skin concern", priority="routine",
                status="requested",
                requested_at=datetime(2026, 10, 20, 8, tzinfo=timezone.utc),
            )
            urgent = Referral(
                encounter_id=second_visit.id, specialty="Fictional cardiology",
                reason="Synthetic consultation", priority="urgent",
                status="requested",
                requested_at=datetime(2026, 10, 21, 10, tzinfo=timezone.utc),
            )
            older_urgent = Referral(
                encounter_id=first_visit.id, specialty="Fictional neurology",
                reason="Synthetic urgent concern", priority="urgent",
                status="requested",
                requested_at=datetime(2026, 10, 20, 9, tzinfo=timezone.utc),
            )
            cancelled = Referral(
                encounter_id=first_visit.id, specialty="Fictional orthopedics",
                reason="Cancelled synthetic consult", priority="urgent",
                status="cancelled",
                requested_at=datetime(2026, 10, 19, 9, tzinfo=timezone.utc),
                cancelled_at=datetime(2026, 10, 19, 10, tzinfo=timezone.utc),
                cancellation_reason="Not needed",
            )
            completed = Referral(
                encounter_id=second_visit.id, specialty="Fictional pulmonology",
                reason="Completed synthetic consult", priority="urgent",
                status="completed",
                requested_at=datetime(2026, 10, 19, 8, tzinfo=timezone.utc),
                completed_at=datetime(2026, 10, 22, 12, tzinfo=timezone.utc),
                seen_on=date(2026, 10, 22),
                follow_up_summary="Synthetic follow-up documented",
            )
            session.add_all([
                routine, urgent, older_urgent, cancelled, completed,
            ])
            session.flush()
            self.routine_id = routine.id
            self.urgent_id = urgent.id
            self.older_urgent_id = older_urgent.id
            self.morgan_id = morgan.id
            self.first_visit_id = first_visit.id
            self.second_visit_id = second_visit.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_only_pending_requests_ordered_by_priority_then_age(self):
        with Session(self.engine) as session:
            rows = list_pending_referrals(session)
            self.assertEqual(
                [referral.id for referral, _, _ in rows],
                [self.older_urgent_id, self.urgent_id, self.routine_id],
            )
            self.assertEqual(
                [visit_date for _, visit_date, _ in rows],
                [date(2026, 10, 20), date(2026, 10, 21), date(2026, 10, 20)],
            )
            self.assertEqual(
                [referral.status for referral, _, _ in rows],
                ["requested", "requested", "requested"],
            )

    def test_patient_identity_and_read_schema(self):
        with Session(self.engine) as session:
            referral, visit_date, patient = list_pending_referrals(session)[1]
            response = PendingReferralRead(
                **ReferralRead.model_validate(referral).model_dump(),
                patient_id=patient.id,
                patient_name=f"{patient.preferred_name or patient.first_name} {patient.last_name}",
                visit_date=visit_date,
            )
            self.assertEqual(response.patient_id, self.morgan_id)
            self.assertEqual(response.patient_name, "Mo Sample")
            self.assertEqual(response.encounter_id, self.second_visit_id)
            self.assertEqual(response.priority, "urgent")
            self.assertEqual(response.status, "requested")

    def test_cancelled_and_completed_requests_leave_worklist(self):
        with Session(self.engine) as session:
            cancel_referral(
                session, self.routine_id,
                ReferralCancel(reason="Patient declined fictional referral"),
            )
            complete_referral(
                session, self.urgent_id,
                ReferralComplete(
                    seen_on=date(2026, 10, 22),
                    follow_up_summary="Synthetic specialist follow-up",
                ),
            )
            complete_referral(
                session, self.older_urgent_id,
                ReferralComplete(
                    seen_on=date(2026, 10, 21),
                    follow_up_summary="Second synthetic specialist follow-up",
                ),
            )
            session.commit()

        with Session(self.engine) as session:
            self.assertEqual(list_pending_referrals(session), [])
            finalized = session.get(Encounter, self.second_visit_id)
            self.assertIsNotNone(finalized.finalized_at)
            self.assertEqual(finalized.assessment, "Fictional follow-up")

    def test_new_request_appears_without_reopening_completed_notes(self):
        with Session(self.engine) as session:
            new_referral = create_referral(
                session, self.first_visit_id,
                ReferralCreate(
                    specialty="Fictional endocrinology",
                    reason="Additional synthetic referral",
                    priority="urgent",
                ),
            )
            session.commit()
            new_id = new_referral.id

        with Session(self.engine) as session:
            ids = [referral.id for referral, _, _ in list_pending_referrals(session)]
            self.assertEqual(
                ids,
                [self.older_urgent_id, self.urgent_id, new_id, self.routine_id],
            )


if __name__ == "__main__":
    unittest.main()
