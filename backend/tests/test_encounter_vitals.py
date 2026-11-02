"""Visit notes retain a snapshot of their own patient's recorded vital signs."""

import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.encounters import apply_encounter_update
from backend.encounter_vitals import (
    link_encounter_vital,
    list_encounter_vitals,
    unlink_encounter_vital,
)
from backend.models import Base, Encounter, EncounterVital, Patient, Vital
from backend.schemas import EncounterUpdate, EncounterVitalLinkCreate, EncounterVitalRead


class EncounterVitalTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="River", last_name="Example",
                date_of_birth=date(1987, 6, 12), sex_at_birth="unknown",
            )
            other = Patient(
                first_name="Morgan", last_name="Sample",
                date_of_birth=date(1986, 2, 17), sex_at_birth="unknown",
            )
            session.add_all([patient, other])
            session.flush()
            self.patient_id = patient.id
            same_day = Vital(
                patient_id=patient.id, recorded_on=date(2026, 10, 20),
                systolic_bp=120, diastolic_bp=80, heart_rate=72,
                temperature_c=36.8, notes="Fictional reading",
            )
            different_day = Vital(
                patient_id=patient.id, recorded_on=date(2026, 10, 19),
                heart_rate=65,
            )
            other_vital = Vital(
                patient_id=other.id, recorded_on=date(2026, 10, 20),
                heart_rate=90,
            )
            note = Encounter(
                patient_id=patient.id, visit_date=date(2026, 10, 20),
                reason_for_visit="Synthetic checkup", assessment="Fictional review",
            )
            session.add_all([same_day, different_day, other_vital, note])
            session.flush()
            self.vital_id, self.different_day_id, self.other_vital_id = (
                same_day.id, different_day.id, other_vital.id
            )
            self.encounter_id = note.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def link(self, session, vital_id=None):
        return link_encounter_vital(
            session, self.encounter_id,
            EncounterVitalLinkCreate(vital_id=vital_id or self.vital_id),
        )

    def test_link_captures_snapshot_and_keeps_chart_record_independent(self):
        with Session(self.engine) as session:
            link = self.link(session)
            session.commit()
            session.refresh(link)
            record = EncounterVitalRead.model_validate(link)
            self.assertEqual(record.recorded_on_at_link, date(2026, 10, 20))
            self.assertEqual(record.systolic_bp_at_link, 120)
            self.assertEqual(record.diastolic_bp_at_link, 80)
            self.assertEqual(record.heart_rate_at_link, 72)
            self.assertEqual(record.temperature_c_at_link, 36.8)
            self.assertEqual(record.notes_at_link, "Fictional reading")
            self.assertIsNotNone(record.linked_at)

        with Session(self.engine) as session:
            vital = session.get(Vital, self.vital_id)
            vital.heart_rate = 110
            vital.notes = "Corrected chart reading"
            session.commit()

        with Session(self.engine) as session:
            saved = list_encounter_vitals(session, self.encounter_id)[0]
            self.assertEqual(saved.heart_rate_at_link, 72)
            self.assertEqual(saved.notes_at_link, "Fictional reading")
            self.assertEqual(session.get(Vital, self.vital_id).heart_rate, 110)

    def test_duplicate_link_returns_conflict(self):
        with Session(self.engine) as session:
            self.link(session)
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session)
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(len(list_encounter_vitals(session, self.encounter_id)), 1)

    def test_database_enforces_unique_pair(self):
        with Session(self.engine) as session:
            for _ in range(2):
                session.add(EncounterVital(
                    encounter_id=self.encounter_id, vital_id=self.vital_id,
                    recorded_on_at_link=date(2026, 10, 20),
                ))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_other_patients_vitals_are_not_accessible(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session, self.other_vital_id)
            self.assertEqual(raised.exception.status_code, 404)
            self.assertEqual(list_encounter_vitals(session, self.encounter_id), [])

    def test_vitals_must_match_visit_date(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session, self.different_day_id)
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(list_encounter_vitals(session, self.encounter_id), [])

    def test_missing_encounter_or_vital_returns_not_found(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session, 9999)
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                link_encounter_vital(
                    session, 9999, EncounterVitalLinkCreate(vital_id=self.vital_id)
                )
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                list_encounter_vitals(session, 9999)
            self.assertEqual(raised.exception.status_code, 404)

    def test_draft_link_can_be_removed_and_relinked(self):
        with Session(self.engine) as session:
            self.link(session)
            session.commit()
        with Session(self.engine) as session:
            unlink_encounter_vital(session, self.encounter_id, self.vital_id)
            session.commit()
            self.assertEqual(list_encounter_vitals(session, self.encounter_id), [])
            self.link(session)
            session.commit()
            self.assertEqual(len(list_encounter_vitals(session, self.encounter_id)), 1)

    def test_missing_link_cannot_be_removed(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                unlink_encounter_vital(session, self.encounter_id, self.vital_id)
            self.assertEqual(raised.exception.status_code, 404)

    def test_finalized_note_keeps_vital_snapshot_read_only(self):
        with Session(self.engine) as session:
            self.link(session)
            session.get(Encounter, self.encounter_id).finalized_at = datetime.now(timezone.utc)
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session)
            self.assertEqual(raised.exception.status_code, 409)
            with self.assertRaises(HTTPException) as raised:
                unlink_encounter_vital(session, self.encounter_id, self.vital_id)
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(len(list_encounter_vitals(session, self.encounter_id)), 1)

    def test_linked_vitals_prevent_moving_draft_visit_date(self):
        with Session(self.engine) as session:
            self.link(session)
            session.commit()

        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                apply_encounter_update(
                    session, self.encounter_id,
                    EncounterUpdate(
                        visit_date=date(2026, 10, 21),
                        reason_for_visit="Synthetic checkup",
                        assessment="Fictional review",
                    ),
                )
            self.assertEqual(raised.exception.status_code, 409)
            session.rollback()

        with Session(self.engine) as session:
            self.assertEqual(
                session.get(Encounter, self.encounter_id).visit_date,
                date(2026, 10, 20),
            )
            unlink_encounter_vital(session, self.encounter_id, self.vital_id)
            apply_encounter_update(
                session, self.encounter_id,
                EncounterUpdate(
                    visit_date=date(2026, 10, 21),
                    reason_for_visit="Synthetic checkup",
                    assessment="Fictional review",
                ),
            )
            session.commit()
            self.assertEqual(
                session.get(Encounter, self.encounter_id).visit_date,
                date(2026, 10, 21),
            )

    def test_link_input_rejects_invalid_ids_and_extra_fields(self):
        for invalid in (0, -1):
            with self.assertRaises(ValidationError):
                EncounterVitalLinkCreate(vital_id=invalid)
        with self.assertRaises(ValidationError):
            EncounterVitalLinkCreate.model_validate(
                {"vital_id": self.vital_id, "encounter_id": self.encounter_id}
            )


if __name__ == "__main__":
    unittest.main()
