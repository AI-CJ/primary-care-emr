"""A patient's activity feed includes only their own chart entries."""

import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import (
    Base, CareGoal, Encounter, FollowUpTask, LabOrder, LabResult,
    Patient, Referral, Vital,
)
from backend.patient_timeline import list_patient_timeline
from backend.schemas import PatientTimelineEntry


class PatientTimelineTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        at = lambda day: datetime(2026, 11, day, 12, tzinfo=timezone.utc)

        with Session(self.engine) as session:
            patient = Patient(
                first_name="Avery", last_name="Example",
                date_of_birth=date(1988, 2, 14), sex_at_birth="unknown",
            )
            other = Patient(
                first_name="Morgan", last_name="Sample",
                date_of_birth=date(1991, 6, 21), sex_at_birth="unknown",
            )
            empty = Patient(
                first_name="Taylor", last_name="Test",
                date_of_birth=date(1999, 5, 2), sex_at_birth="unknown",
            )
            session.add_all([patient, other, empty])
            session.flush()
            self.patient_id, self.empty_id = patient.id, empty.id

            visit = Encounter(
                patient_id=patient.id, visit_date=date(2026, 11, 5),
                reason_for_visit="Synthetic follow-up",
            )
            older = Encounter(
                patient_id=patient.id, visit_date=date(2026, 10, 1),
                reason_for_visit="Fictional intake", finalized_at=at(6),
            )
            other_visit = Encounter(
                patient_id=other.id, visit_date=date(2026, 11, 9),
                reason_for_visit="Other chart visit",
            )
            session.add_all([visit, older, other_visit])
            session.flush()
            session.add(Vital(patient_id=patient.id, recorded_on=date(2026, 11, 4)))
            order = LabOrder(
                encounter_id=visit.id, test_name="Synthetic blood panel",
                priority="routine", status="resulted", ordered_at=at(5),
            )
            other_order = LabOrder(
                encounter_id=other_visit.id, test_name="Other chart lab",
                priority="urgent", status="ordered", ordered_at=at(9),
            )
            session.add_all([order, other_order])
            session.flush()
            session.add_all([
                LabResult(
                    lab_order_id=order.id, collected_on=date(2026, 11, 6),
                    result_text="Synthetic result text", reported_at=at(7),
                ),
                Referral(
                    encounter_id=visit.id, specialty="Fictional dermatology",
                    reason="Synthetic consult", priority="routine",
                    status="requested", requested_at=at(6),
                ),
                CareGoal(
                    patient_id=patient.id, title="Synthetic care goal",
                    status="active", created_at=at(3),
                ),
                FollowUpTask(
                    patient_id=patient.id, title="Synthetic follow-up task",
                    status="open", created_at=at(8),
                ),
                FollowUpTask(
                    patient_id=other.id, title="Other chart task",
                    status="open", created_at=at(9),
                ),
            ])
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_combines_entries_in_date_order_without_cross_patient_data(self):
        with Session(self.engine) as session:
            entries = list_patient_timeline(session, self.patient_id)
            self.assertEqual(len(entries), 8)
            self.assertEqual(entries[0].kind, "follow_up")
            self.assertEqual(
                [entry.occurred_on for entry in entries],
                sorted((entry.occurred_on for entry in entries), reverse=True),
            )
            self.assertEqual(
                {entry.kind for entry in entries},
                {"visit", "vitals", "lab_order", "lab_result", "referral", "care_goal", "follow_up"},
            )
            self.assertTrue(all("Other chart" not in entry.title for entry in entries))
            self.assertTrue(all("result text" not in entry.title for entry in entries))

    def test_statuses_and_serialization_reflect_current_chart(self):
        with Session(self.engine) as session:
            entries = list_patient_timeline(session, self.patient_id)
            visits = [entry for entry in entries if entry.kind == "visit"]
            self.assertEqual({entry.status for entry in visits}, {"draft", "finalized"})
            order = next(entry for entry in entries if entry.kind == "lab_order")
            self.assertEqual(order.status, "resulted")
            result = next(entry for entry in entries if entry.kind == "lab_result")
            self.assertEqual(result.status, "reported")
            self.assertEqual(
                PatientTimelineEntry.model_validate(result).model_dump(mode="json")["occurred_on"],
                "2026-11-07",
            )

    def test_limit_empty_chart_and_missing_patient(self):
        with Session(self.engine) as session:
            self.assertEqual(len(list_patient_timeline(session, self.patient_id, limit=2)), 2)
            self.assertEqual(list_patient_timeline(session, self.empty_id), [])
            with self.assertRaises(HTTPException) as raised:
                list_patient_timeline(session, 999999)
            self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
