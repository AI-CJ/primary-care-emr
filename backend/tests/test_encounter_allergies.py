"""Visit allergy references preserve a patient's allergy history."""

import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.encounter_allergies import (
    link_encounter_allergy,
    list_encounter_allergies,
    unlink_encounter_allergy,
)
from backend.models import Base, Encounter, EncounterAllergy, Allergy, Patient
from backend.schemas import EncounterAllergyLinkCreate, EncounterAllergyRead


class EncounterAllergyTests(unittest.TestCase):
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
            allergy = Allergy(
                patient_id=patient.id, allergen="Fictional pollen", reaction="Sneezing",
                severity="mild", status="active", onset_date=date(2025, 3, 1),
                notes="Synthetic example",
            )
            other_allergy = Allergy(
                patient_id=other.id, allergen="Fictional dye",
                severity="unknown", status="active",
            )
            note = Encounter(
                patient_id=patient.id, visit_date=date(2026, 10, 20),
                reason_for_visit="Synthetic checkup",
            )
            session.add_all([allergy, other_allergy, note])
            session.flush()
            self.allergy_id = allergy.id
            self.other_allergy_id = other_allergy.id
            self.encounter_id = note.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def link(self, session, allergy_id=None):
        return link_encounter_allergy(
            session, self.encounter_id,
            EncounterAllergyLinkCreate(
                allergy_id=allergy_id or self.allergy_id
            ),
        )

    def test_link_preserves_allergy_snapshot_after_chart_update(self):
        with Session(self.engine) as session:
            link = self.link(session)
            session.commit()
            session.refresh(link)
            snapshot = EncounterAllergyRead.model_validate(link)
            self.assertEqual(snapshot.allergen_at_link, "Fictional pollen")
            self.assertEqual(snapshot.reaction_at_link, "Sneezing")
            self.assertEqual(snapshot.severity_at_link, "mild")
            self.assertEqual(snapshot.status_at_link, "active")
            self.assertEqual(snapshot.onset_date_at_link, date(2025, 3, 1))
            self.assertEqual(snapshot.notes_at_link, "Synthetic example")
            self.assertIsNotNone(snapshot.linked_at)

        with Session(self.engine) as session:
            allergy = session.get(Allergy, self.allergy_id)
            allergy.severity = "severe"
            allergy.status = "inactive"
            allergy.reaction = "Changed later"
            session.commit()

        with Session(self.engine) as session:
            saved = list_encounter_allergies(session, self.encounter_id)[0]
            self.assertEqual(saved.severity_at_link, "mild")
            self.assertEqual(saved.status_at_link, "active")
            self.assertEqual(saved.reaction_at_link, "Sneezing")

    def test_duplicate_link_is_rejected(self):
        with Session(self.engine) as session:
            self.link(session)
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session)
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(len(list_encounter_allergies(session, self.encounter_id)), 1)

    def test_database_rejects_duplicate_pair(self):
        with Session(self.engine) as session:
            for _ in range(2):
                session.add(EncounterAllergy(
                    encounter_id=self.encounter_id,
                    allergy_id=self.allergy_id,
                    allergen_at_link="Fictional pollen", severity_at_link="mild", status_at_link="active",
                ))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_cannot_link_allergy_from_another_patient(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session, self.other_allergy_id)
            self.assertEqual(raised.exception.status_code, 404)
            self.assertEqual(list_encounter_allergies(session, self.encounter_id), [])

    def test_missing_allergy_and_note_return_404(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                self.link(session, 9999)
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                link_encounter_allergy(
                    session, 9999, EncounterAllergyLinkCreate(allergy_id=self.allergy_id)
                )
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException) as raised:
                list_encounter_allergies(session, 9999)
            self.assertEqual(raised.exception.status_code, 404)

    def test_draft_link_can_be_removed_and_added_again(self):
        with Session(self.engine) as session:
            self.link(session)
            session.commit()
        with Session(self.engine) as session:
            unlink_encounter_allergy(session, self.encounter_id, self.allergy_id)
            session.commit()
            self.assertEqual(list_encounter_allergies(session, self.encounter_id), [])
            self.link(session)
            session.commit()
            self.assertEqual(len(list_encounter_allergies(session, self.encounter_id)), 1)

    def test_missing_link_cannot_be_removed(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as raised:
                unlink_encounter_allergy(session, self.encounter_id, self.allergy_id)
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
                unlink_encounter_allergy(session, self.encounter_id, self.allergy_id)
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(len(list_encounter_allergies(session, self.encounter_id)), 1)

    def test_link_input_rejects_invalid_values_and_extra_fields(self):
        for invalid in (0, -1):
            with self.assertRaises(ValidationError):
                EncounterAllergyLinkCreate(allergy_id=invalid)
        with self.assertRaises(ValidationError):
            EncounterAllergyLinkCreate.model_validate(
                {"allergy_id": self.allergy_id, "encounter_id": self.encounter_id}
            )


if __name__ == "__main__":
    unittest.main()
