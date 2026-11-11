"""Portal visit summaries omit drafts and clinical note text."""

import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.encounters import list_portal_preview_visits
from backend.models import Base, Encounter, Patient


class PortalPreviewVisitsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Avery", last_name="Example",
                date_of_birth=date(1990, 3, 17), sex_at_birth="unknown",
            )
            other = Patient(
                first_name="River", last_name="Sample",
                date_of_birth=date(1984, 7, 9), sex_at_birth="unknown",
            )
            empty = Patient(
                first_name="Taylor", last_name="Test",
                date_of_birth=date(1998, 2, 21), sex_at_birth="unknown",
            )
            session.add_all([patient, other, empty])
            session.flush()
            self.patient_id = patient.id
            self.empty_id = empty.id

            finalized = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
            for day in range(1, 8):
                session.add(Encounter(
                    patient_id=patient.id,
                    visit_date=date(2026, 10, day),
                    reason_for_visit=f"Fictional visit {day}",
                    subjective="Private synthetic history",
                    objective="Private synthetic exam",
                    assessment="Private synthetic assessment",
                    plan="Private synthetic plan",
                    patient_instructions=("Bring fictional readings next time" if day == 7 else None),
                    finalized_at=finalized,
                ))
            session.add_all([
                Encounter(
                    patient_id=patient.id, visit_date=date(2026, 11, 1),
                    reason_for_visit="Unfinalized visit",
                    subjective="Unfinished synthetic history",
                    patient_instructions="Unreleased draft instructions",
                ),
                Encounter(
                    patient_id=other.id, visit_date=date(2026, 11, 9),
                    reason_for_visit="Another patient's visit",
                    patient_instructions="Another patient's instructions",
                    finalized_at=finalized,
                ),
            ])
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_only_recent_finalized_visits_for_patient(self):
        with Session(self.engine) as session:
            visits = list_portal_preview_visits(session, self.patient_id)

        self.assertEqual(
            [visit.reason_for_visit for visit in visits],
            [f"Fictional visit {day}" for day in (7, 6, 5, 4, 3)],
        )

    def test_response_does_not_include_clinical_note_fields(self):
        with Session(self.engine) as session:
            visits = list_portal_preview_visits(session, self.patient_id)

        for visit in visits:
            self.assertEqual(
                set(visit.model_dump(mode="json")),
                {"id", "visit_date", "reason_for_visit", "patient_instructions"},
            )
        self.assertEqual(visits[0].patient_instructions, "Bring fictional readings next time")
        self.assertIsNone(visits[1].patient_instructions)
        self.assertNotIn("Private synthetic", repr(visits))
        self.assertNotIn("Unreleased draft", repr(visits))
        self.assertNotIn("Another patient", repr(visits))

    def test_same_day_visits_are_ordered_by_id(self):
        with Session(self.engine) as session:
            session.add(Encounter(
                patient_id=self.patient_id, visit_date=date(2026, 10, 7),
                reason_for_visit="Second same-day visit",
                finalized_at=datetime(2026, 11, 5, tzinfo=timezone.utc),
            ))
            session.commit()
            visits = list_portal_preview_visits(session, self.patient_id)

        self.assertEqual(visits[0].reason_for_visit, "Second same-day visit")
        self.assertEqual(visits[1].reason_for_visit, "Fictional visit 7")

    def test_empty_chart_and_missing_patient(self):
        with Session(self.engine) as session:
            self.assertEqual(list_portal_preview_visits(session, self.empty_id), [])
            with self.assertRaises(HTTPException) as raised:
                list_portal_preview_visits(session, 999999)
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
