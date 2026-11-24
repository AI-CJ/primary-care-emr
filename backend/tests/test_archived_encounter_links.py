"""Archived charts preserve visit-linked snapshots and reject link changes."""

import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.encounter_allergies import (
    link_encounter_allergy,
    list_encounter_allergies,
    unlink_encounter_allergy,
)
from backend.encounter_medications import (
    link_encounter_medication,
    list_encounter_medications,
    unlink_encounter_medication,
)
from backend.encounter_problems import (
    link_encounter_problem,
    list_encounter_problems,
    unlink_encounter_problem,
)
from backend.encounter_vitals import (
    link_encounter_vital,
    list_encounter_vitals,
    unlink_encounter_vital,
)
from backend.models import Allergy, Base, Encounter, Medication, Patient, Problem, Vital
from backend.schemas import (
    EncounterAllergyLinkCreate,
    EncounterMedicationLinkCreate,
    EncounterProblemLinkCreate,
    EncounterVitalLinkCreate,
)


class ArchivedEncounterLinkTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        visit_date = date(2026, 11, 24)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Archive", last_name="Example",
                date_of_birth=date(1988, 4, 12), sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            encounter = Encounter(
                patient_id=patient.id, visit_date=visit_date,
                reason_for_visit="Synthetic archive regression visit",
            )
            problems = [
                Problem(patient_id=patient.id, name=name, status="active")
                for name in ("Synthetic condition one", "Synthetic condition two")
            ]
            medications = [
                Medication(patient_id=patient.id, name=name, status="active")
                for name in ("Synthetic medication one", "Synthetic medication two")
            ]
            allergies = [
                Allergy(patient_id=patient.id, allergen=name, status="active")
                for name in ("Synthetic allergen one", "Synthetic allergen two")
            ]
            vitals = [
                Vital(patient_id=patient.id, recorded_on=visit_date, heart_rate=rate)
                for rate in (70, 74)
            ]
            session.add_all([encounter, *problems, *medications, *allergies, *vitals])
            session.flush()
            self.patient_id = patient.id
            self.encounter_id = encounter.id
            self.problem_ids = [row.id for row in problems]
            self.medication_ids = [row.id for row in medications]
            self.allergy_ids = [row.id for row in allergies]
            self.vital_ids = [row.id for row in vitals]
            link_encounter_problem(
                session, encounter.id,
                EncounterProblemLinkCreate(problem_id=problems[0].id),
            )
            link_encounter_medication(
                session, encounter.id,
                EncounterMedicationLinkCreate(medication_id=medications[0].id),
            )
            link_encounter_allergy(
                session, encounter.id,
                EncounterAllergyLinkCreate(allergy_id=allergies[0].id),
            )
            link_encounter_vital(
                session, encounter.id,
                EncounterVitalLinkCreate(vital_id=vitals[0].id),
            )
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_archive_blocks_link_and_unlink_then_reactivation_restores_them(self):
        with Session(self.engine) as session:
            session.get(Patient, self.patient_id).archived_at = datetime.now(timezone.utc)
            session.commit()

        link_cases = (
            (link_encounter_problem,
             EncounterProblemLinkCreate(problem_id=self.problem_ids[1])),
            (link_encounter_medication,
             EncounterMedicationLinkCreate(medication_id=self.medication_ids[1])),
            (link_encounter_allergy,
             EncounterAllergyLinkCreate(allergy_id=self.allergy_ids[1])),
            (link_encounter_vital,
             EncounterVitalLinkCreate(vital_id=self.vital_ids[1])),
        )
        unlink_cases = (
            (unlink_encounter_problem, self.problem_ids[0]),
            (unlink_encounter_medication, self.medication_ids[0]),
            (unlink_encounter_allergy, self.allergy_ids[0]),
            (unlink_encounter_vital, self.vital_ids[0]),
        )
        with Session(self.engine) as session:
            for operation, payload in link_cases:
                with self.subTest(link=operation.__name__):
                    with self.assertRaises(HTTPException) as raised:
                        operation(session, self.encounter_id, payload)
                    self.assertEqual(raised.exception.status_code, 409)
                    self.assertIn("Archived", raised.exception.detail)
            for operation, resource_id in unlink_cases:
                with self.subTest(unlink=operation.__name__):
                    with self.assertRaises(HTTPException) as raised:
                        operation(session, self.encounter_id, resource_id)
                    self.assertEqual(raised.exception.status_code, 409)
                    self.assertIn("Archived", raised.exception.detail)
            self.assertEqual(len(list_encounter_problems(session, self.encounter_id)), 1)
            self.assertEqual(len(list_encounter_medications(session, self.encounter_id)), 1)
            self.assertEqual(len(list_encounter_allergies(session, self.encounter_id)), 1)
            self.assertEqual(len(list_encounter_vitals(session, self.encounter_id)), 1)

        with Session(self.engine) as session:
            session.get(Patient, self.patient_id).archived_at = None
            session.commit()
        with Session(self.engine) as session:
            for operation, payload in link_cases:
                operation(session, self.encounter_id, payload)
            for operation, resource_id in unlink_cases:
                operation(session, self.encounter_id, resource_id)
            session.commit()
            self.assertEqual(
                [row.problem_id for row in list_encounter_problems(session, self.encounter_id)],
                [self.problem_ids[1]],
            )
            self.assertEqual(
                [row.medication_id for row in list_encounter_medications(session, self.encounter_id)],
                [self.medication_ids[1]],
            )
            self.assertEqual(
                [row.allergy_id for row in list_encounter_allergies(session, self.encounter_id)],
                [self.allergy_ids[1]],
            )
            self.assertEqual(
                [row.vital_id for row in list_encounter_vitals(session, self.encounter_id)],
                [self.vital_ids[1]],
            )


if __name__ == "__main__":
    unittest.main()
