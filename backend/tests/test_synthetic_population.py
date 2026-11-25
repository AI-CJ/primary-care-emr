"""Invariants for the generated fictional clinic population."""
from datetime import date
from unittest import TestCase, skipUnless

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.icd10_catalog import CATALOG_PATH, lookup_code
from backend.models import (
    Base, Patient, Problem, Medication, MedicationIndication,
    Appointment, AppointmentStatusChange, Encounter, EncounterProblem,
    Vital, LabOrder, LabOrderIndication, LabResult, PatientBackground, ImagingReport,
)
from backend.synthetic_population import ADDITIONAL_CONDITIONS, CONDITIONS, POPULATION_SIZE, add_clinic_population


AS_OF = date(2026, 11, 25)


class SyntheticPopulationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)
        with Session(cls.engine) as session:
            refs = [
                Patient(first_name="Jordan", last_name="Lee", date_of_birth=date(1984, 3, 12),
                        sex_at_birth="unknown"),
                Patient(first_name="Maria", last_name="Thompson", date_of_birth=date(1957, 8, 24),
                        sex_at_birth="unknown"),
                Patient(first_name="Devin", last_name="Brooks", date_of_birth=date(2001, 11, 5),
                        sex_at_birth="unknown"),
            ]
            session.add_all(refs)
            session.flush()
            add_clinic_population(session, as_of=AS_OF, reference_patients=tuple(refs))
            session.commit()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_population_and_longitudinal_coverage(self):
        with Session(self.engine) as session:
            patients = session.scalars(select(Patient)).all()
            ids = {p.id for p in patients}
            self.assertEqual(len(patients), POPULATION_SIZE)
            self.assertEqual(len({(p.first_name, p.last_name) for p in patients}), POPULATION_SIZE)
            self.assertEqual({p.patient_id for p in session.scalars(select(Vital))}, ids)
            self.assertEqual({p.patient_id for p in session.scalars(select(Encounter))}, ids)
            ages = [AS_OF.year - p.date_of_birth.year -
                    ((AS_OF.month, AS_OF.day) < (p.date_of_birth.month, p.date_of_birth.day))
                    for p in patients]
            self.assertTrue(all(18 <= age <= 94 for age in ages))
            self.assertGreaterEqual(max(ages), 85)
            self.assertLessEqual(min(ages), 21)
            problems = session.scalars(select(Problem)).all()
            active_ids = {p.patient_id for p in problems if p.status == "active"}
            self.assertGreater(len(active_ids), 180)
            self.assertGreater(len(ids - active_ids), 40)
            self.assertGreaterEqual(len({p.icd10_code for p in problems}), 12)
            self.assertTrue(any(p.status == "resolved" for p in problems))

    def test_associations_are_same_patient_and_use_recorded_codes(self):
        with Session(self.engine) as session:
            problems = {p.id: p for p in session.scalars(select(Problem))}
            meds = {m.id: m for m in session.scalars(select(Medication))}
            notes = {n.id: n for n in session.scalars(select(Encounter))}
            orders = {o.id: o for o in session.scalars(select(LabOrder))}
            linked_meds = set()
            for link in session.scalars(select(MedicationIndication)):
                p = problems[link.problem_id]
                self.assertEqual(meds[link.medication_id].patient_id, p.patient_id)
                self.assertEqual(link.icd10_code, p.icd10_code)
                linked_meds.add(link.medication_id)
            self.assertEqual(linked_meds, set(meds))
            linked_orders = set()
            for link in session.scalars(select(LabOrderIndication)):
                p = problems[link.problem_id]
                self.assertEqual(notes[orders[link.lab_order_id].encounter_id].patient_id, p.patient_id)
                self.assertEqual(link.icd10_code, p.icd10_code)
                linked_orders.add(link.lab_order_id)
            self.assertEqual(linked_orders, set(orders))
            for link in session.scalars(select(EncounterProblem)):
                self.assertEqual(notes[link.encounter_id].patient_id, problems[link.problem_id].patient_id)
                self.assertEqual(link.icd10_code_at_link, problems[link.problem_id].icd10_code)
            self.assertGreater(len(meds), 100)
            self.assertGreater(len(orders), 80)

    def test_chronology_and_no_double_bookings(self):
        with Session(self.engine) as session:
            appointments = {a.id: a for a in session.scalars(select(Appointment))}
            slots = {(a.scheduled_date, a.start_time) for a in appointments.values()}
            self.assertEqual(len(slots), len(appointments))
            for note in session.scalars(select(Encounter)):
                a = appointments[note.appointment_id]
                self.assertEqual(note.visit_date, a.scheduled_date)
                self.assertEqual(note.patient_id, a.patient_id)
                self.assertEqual(a.status, "completed")
                self.assertLess(note.visit_date, AS_OF)
            for result in session.scalars(select(LabResult)):
                self.assertLessEqual(result.collected_on, result.reported_at.date())
                if result.released_at is not None:
                    self.assertLessEqual(result.reported_at, result.released_at)
            for vital in session.scalars(select(Vital)):
                self.assertGreater(vital.systolic_bp, vital.diastolic_bp)
                self.assertLess(vital.recorded_on, AS_OF)
            statuses = {}
            for change in session.scalars(select(AppointmentStatusChange).order_by(
                    AppointmentStatusChange.appointment_id, AppointmentStatusChange.changed_at)):
                statuses.setdefault(change.appointment_id, []).append(change.new_status)
            for a in appointments.values():
                expected = ["scheduled", "checked_in", "completed"] if a.status == "completed" else ["scheduled"]
                self.assertEqual(statuses[a.id], expected)

    @skipUnless(CATALOG_PATH.exists(), "Prepare the pinned ICD-10-CM catalog to verify reference titles")
    def test_condition_codes_and_titles_exist_in_official_catalog(self):
        for condition in (*CONDITIONS, *ADDITIONAL_CONDITIONS):
            with self.subTest(code=condition.code):
                code = lookup_code(condition.code)
                self.assertEqual(code.title, condition.title)


    def test_background_and_imaging_depth(self):
        with Session(self.engine) as session:
            patients = {p.id: p for p in session.scalars(select(Patient))}
            backgrounds = {p.patient_id: p for p in session.scalars(select(PatientBackground))}
            self.assertEqual(set(backgrounds), set(patients))
            for background in backgrounds.values():
                for value in (background.medical_history, background.surgical_history,
                              background.family_history, background.social_history, background.care_context):
                    self.assertGreater(len(value.strip()), 15)
                self.assertLessEqual(background.reviewed_on, AS_OF)
            self.assertGreater(len({b.social_history for b in backgrounds.values()}), 300)
            self.assertGreater(len({b.care_context for b in backgrounds.values()}), 50)
            reports = session.scalars(select(ImagingReport)).all()
            self.assertGreater(len(reports), 50)
            self.assertLess(len({r.patient_id for r in reports}), len(patients))
            self.assertGreaterEqual(len({r.modality for r in reports}), 3)
            self.assertTrue(any(r.shared_on is None for r in reports))
            for report in reports:
                self.assertLess(patients[report.patient_id].date_of_birth, report.performed_on)
                self.assertLessEqual(report.performed_on, report.reported_on)
                self.assertLessEqual(report.reported_on, backgrounds[report.patient_id].reviewed_on)
                if report.shared_on:
                    self.assertLessEqual(report.reported_on, report.shared_on)
                    self.assertLessEqual(report.shared_on, AS_OF)
                self.assertTrue(report.indication and report.findings and report.impression)
            problems = {}
            for p in session.scalars(select(Problem)):
                problems.setdefault(p.patient_id, set()).add(p.icd10_code)
            for codes in problems.values():
                self.assertFalse({"E11.9", "R73.03"} <= codes)
            for code, modality in (("M81.0", "DXA"), ("K76.0", "Ultrasound")):
                expected = {patient_id for patient_id, codes in problems.items() if code in codes}
                self.assertTrue(expected, code)
                actual = {r.patient_id for r in reports if r.modality == modality}
                self.assertTrue(expected <= actual)
            old_meds = session.scalars(select(Medication).where(Medication.status == "discontinued")).all()
            self.assertGreater(len(old_meds), 15)
            for medication in old_meds:
                self.assertLessEqual(medication.start_date, medication.end_date)
                self.assertTrue(medication.instructions)
