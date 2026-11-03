"""Visit medication references preserve a patient's medication history."""

import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.encounter_medications import (
    link_encounter_medication,
    list_encounter_medications,
    unlink_encounter_medication,
)
from backend.models import Base, Encounter, EncounterMedication, Medication, Patient
from backend.schemas import EncounterMedicationLinkCreate, EncounterMedicationRead


class EncounterMedicationTests(unittest.TestCase):
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
            medication = Medication(
                patient_id=patient.id, name="Fictional inhaler", strength="90 mcg",
                dose="Two puffs", route="Inhaled", frequency="As needed",
                status="active", start_date=date(2026, 10, 1),
                instructions="Fictional medication entry",
            )
            other_medication = Medication(
                patient_id=other.id, name="Fictional tablet", status="active"
            )
            note = Encounter(
                patient_id=patient.id, visit_date=date(2026, 10, 20),
                reason_for_visit="Synthetic checkup",
            )
            session.add_all([medication, other_medication, note])
            session.flush()
            self.medication_id = medication.id
            self.other_medication_id = other_medication.id
            self.encounter_id = note.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def link(self, session, medication_id=None):
        return link_encounter_medication(
            session, self.encounter_id,
            EncounterMedicationLinkCreate(
                medication_id=medication_id or self.medication_id
            ),
        )

    def test_link_preserves_medication_snapshot_after_chart_update(self):
        with Session(self.engine) as session:
            link = self.link(session)
            session.commit()
            session.refresh(link)
            record = EncounterMedicationRead.model_validate(link)
            self.assertEqual(record.name_at_link, "Fictional inhaler")
            self.assertEqual(record.strength_at_link, "90 mcg")
            self.assertEqual(record.frequency_at_link, "As needed")
            self.assertEqual(record.status_at_link, "active")
            self.assertEqual(record.start_date_at_link, date(2026, 10, 1))
            self.assertEqual(record.instructions_at_link, "Fictional medication entry")
            self.assertIsNotNone(record.linked_at)

        with Session(self.engine) as session:
            medication = session.get(Medication, self.medication_id)
            medication.status = "discontinued"
            medication.dose = "Changed on chart"
            session.commit()

        with Session(self.engine) as session:
            saved = list_encounter_medications(session, self.encounter_id)[0]
            self.assertEqual(saved.status_at_link, "active")
            self.assertEqual(saved.dose_at_link, "Two puffs")
            self.assertEqual(session.get(Medication, self.medication_id).dose, "Changed on chart")

    def test_duplicate_link_is_rejected(self):
        with Session(self.engine) as session:
            self.link(session)
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session)
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(len(list_encounter_medications(session, self.encounter_id)), 1)

    def test_database_rejects_duplicate_pair(self):
        with Session(self.engine) as session:
            for _ in range(2):
                session.add(EncounterMedication(
                    encounter_id=self.encounter_id,
                    medication_id=self.medication_id,
                    name_at_link="Fictional inhaler", status_at_link="active",
                ))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_cannot_link_medication_from_another_patient(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session, self.other_medication_id)
            self.assertEqual(raised.exception.status_code, 404)
            self.assertEqual(list_encounter_medications(session, self.encounter_id), [])

    def test_missing_medication_and_note_return_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session, 9999)
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                link_encounter_medication(
                    session, 9999, EncounterMedicationLinkCreate(medication_id=self.medication_id)
                )
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                list_encounter_medications(session, 9999)
            self.assertEqual(raised.exception.status_code, 404)

    def test_draft_link_can_be_removed_and_added_again(self):
        with Session(self.engine) as session:
            self.link(session)
            session.commit()
        with Session(self.engine) as session:
            unlink_encounter_medication(session, self.encounter_id, self.medication_id)
            session.commit()
            self.assertEqual(list_encounter_medications(session, self.encounter_id), [])
            self.link(session)
            session.commit()
            self.assertEqual(len(list_encounter_medications(session, self.encounter_id)), 1)

    def test_missing_link_cannot_be_removed(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                unlink_encounter_medication(session, self.encounter_id, self.medication_id)
            self.assertEqual(raised.exception.status_code, 404)

    def test_finalized_note_links_are_read_only(self):
        with Session(self.engine) as session:
            self.link(session)
            session.get(Encounter, self.encounter_id).finalized_at = datetime.now(timezone.utc)
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session)
            self.assertEqual(raised.exception.status_code, 409)
            with self.assertRaises(HTTPException) as raised:
                unlink_encounter_medication(session, self.encounter_id, self.medication_id)
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(len(list_encounter_medications(session, self.encounter_id)), 1)

    def test_link_input_rejects_invalid_values_and_extra_fields(self):
        for invalid in (0, -1):
            with self.assertRaises(ValidationError):
                EncounterMedicationLinkCreate(medication_id=invalid)
        with self.assertRaises(ValidationError):
            EncounterMedicationLinkCreate.model_validate(
                {"medication_id": self.medication_id, "encounter_id": self.encounter_id}
            )


if __name__ == "__main__":
    unittest.main()
