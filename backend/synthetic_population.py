"""Deterministic, fictional outpatient charts for the public and local examples.

This is an authored scenario generator, not a population prevalence model or
clinical recommendation engine. It never imports real patient records.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from random import Random

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.chart_context_seed import daily_context, seed_chart_backgrounds
from backend.models import (
    Allergy, Appointment, AppointmentStatusChange, CareGoal, CareGoalProgress,
    Encounter, EncounterProblem, FollowUpTask, LabOrder, LabOrderIndication,
    LabResult, Medication, MedicationIndication, Patient, Problem, Referral, Vital,
)

POPULATION_SIZE = 400
REFERENCE_PATIENTS = 3
SEED = 20261125
CODE_RELEASE = "FY2027"

FIRST_NAMES = (
    "Amara Beatrice Camila Celeste Daphne Elena Farah Gabriela Hannah Imani "
    "Isabel Jade Keiko Leila Lucia Maya Nadia Naomi Noor Priya Rosa Samira "
    "Sofia Talia Valerie Vivian Yara Zoe Adrian Antonio Caleb Daniel Elias "
    "Emilio Ethan Felix Gabriel Hassan Hugo Isaac Julian Kai Leon Malik "
    "Mateo Micah Nikhil Omar Rafael Ravi Samuel Theo Victor Wesley Yusuf "
    "Alex Casey Ellis Jamie Morgan Quinn Riley Sage Taylor"
).split()
LAST_NAMES = (
    "Adams Ahmed Alvarez Anderson Baker Bennett Brown Campbell Carter Chen "
    "Choi Collins Cooper Cruz Davis Diaz Edwards Evans Flores Garcia Gomez "
    "Gonzalez Green Hall Harris Hernandez Hill Hughes Jackson Kim Kumar "
    "Lewis Martin Mitchell Morales Nguyen Ortiz Patel Perez Phillips "
    "Ramirez Rivera Robinson Ross Santos Shah Singh Smith Sullivan "
    "Torres Turner Walker White Wilson Wong Young"
).split()


@dataclass(frozen=True)
class Condition:
    code: str
    title: str
    name: str
    minimum_age: int
    concern: str
    goal: str
    medication: tuple[str, str, str, str] | None = None
    lab: tuple[str, str, str] | None = None
    referral: tuple[str, str] | None = None


# Code descriptions are checked against the pinned official catalog in tests.
# Medication and test associations are explicit authored scenarios, never inferred
# from a drug or test name. None of these examples constitutes treatment advice.
CONDITIONS = (
    Condition("I10", "Essential (primary) hypertension", "Essential hypertension", 30,
              "Home blood pressure readings were brought to the visit.",
              "Review the home blood pressure log",
              ("Amlodipine", "5 mg", "oral", "Daily"),
              ("Basic metabolic panel", "Creatinine {value:.2f} mg/dL; potassium 4.2 mmol/L.", "Review renal function in hypertension")),
    Condition("E78.5", "Hyperlipidemia, unspecified", "Hyperlipidemia", 30,
              "Discussed previous cholesterol results and interval activity.",
              "Review lipid results at follow-up",
              ("Atorvastatin", "20 mg", "oral", "Nightly"),
              ("Lipid panel", "LDL {value:.0f} mg/dL; HDL 49 mg/dL.", "Lipid monitoring")),
    Condition("E11.9", "Type 2 diabetes mellitus without complications", "Type 2 diabetes", 35,
              "Reviewed glucose readings and barriers to routine meals.",
              "Bring the glucose log to the next review",
              ("Metformin", "500 mg", "oral", "Twice daily"),
              ("Hemoglobin A1c", "Hemoglobin A1c {value:.1f}%.", "Glycemic monitoring")),
    Condition("E03.9", "Hypothyroidism, unspecified", "Hypothyroidism", 18,
              "Discussed energy level and medication-taking routine.",
              "Review thyroid laboratory results",
              ("Levothyroxine", "50 mcg", "oral", "Daily"),
              ("TSH", "TSH {value:.2f} mIU/L.", "Thyroid monitoring")),
    Condition("J45.909", "Unspecified asthma, uncomplicated", "Asthma", 18,
              "Reviewed intermittent respiratory symptoms and inhaler use.",
              "Review symptom frequency and inhaler technique",
              ("Budesonide", "180 mcg", "inhalation", "One inhalation twice daily")),
    Condition("J30.9", "Allergic rhinitis, unspecified", "Allergic rhinitis", 18,
              "Reports intermittent nasal congestion with environmental triggers.",
              "Track symptom triggers",
              ("Cetirizine", "10 mg", "oral", "Daily as needed")),
    Condition("K21.9", "Gastro-esophageal reflux disease without esophagitis", "Gastroesophageal reflux", 18,
              "Discussed intermittent reflux symptoms and meal timing.",
              "Review reflux symptom diary",
              ("Omeprazole", "20 mg", "oral", "Daily")),
    Condition("G43.909", "Migraine, unspecified, not intractable, without status migrainosus", "Migraine", 18,
              "Reviewed headache frequency, duration and reported triggers.",
              "Record headache frequency before the next visit"),
    Condition("F41.9", "Anxiety disorder, unspecified", "Anxiety", 18,
              "Discussed sleep, daily routines and current stressors.",
              "Review coping strategies and functional symptoms",
              ("Sertraline", "50 mg", "oral", "Daily"),
              referral=("Behavioral health", "Discuss counseling options")),
    Condition("M17.11", "Unilateral primary osteoarthritis, right knee", "Right knee osteoarthritis", 50,
              "Reports intermittent knee discomfort with stairs and longer walks.",
              "Review mobility and functional goals",
              referral=("Physical therapy", "Assess knee mobility and function")),
    Condition("M54.50", "Low back pain, unspecified", "Low back pain", 18,
              "Discussed intermittent back discomfort during daily activities.",
              "Review activity tolerance",
              referral=("Physical therapy", "Evaluate functional mobility")),
    Condition("G47.33", "Obstructive sleep apnea (adult) (pediatric)", "Obstructive sleep apnea", 30,
              "Reviewed sleep quality and reported positive airway pressure use.",
              "Review sleep equipment use",
              referral=("Sleep medicine", "Review sleep treatment follow-up")),
    Condition("D50.9", "Iron deficiency anemia, unspecified", "Iron deficiency anemia", 18,
              "Discussed fatigue, previous laboratory findings and follow-up.",
              "Review repeat blood counts",
              lab=("Complete blood count", "Hemoglobin {value:.1f} g/dL; MCV 78 fL.", "Anemia follow-up")),
    Condition("E55.9", "Vitamin D deficiency, unspecified", "Vitamin D deficiency", 18,
              "Reviewed prior vitamin D results and supplement history.",
              "Review vitamin D results",
              lab=("25-hydroxy vitamin D", "25-hydroxy vitamin D {value:.0f} ng/mL.", "Vitamin D monitoring")),
    Condition("J06.9", "Acute upper respiratory infection, unspecified", "Upper respiratory infection", 18,
              "Previous respiratory symptoms have resolved.",
              "Review only if symptoms recur"),
)


# Additional, selectively assigned authored scenarios. They are not diagnoses
# calculated for actual patients, and the generator excludes conflicting labels.
ADDITIONAL_CONDITIONS = (
    Condition("R73.03", "Prediabetes", "Prediabetes", 30,
              "Discussed prior borderline glucose measurements and meal routines.",
              "Review interval glucose measurements",
              lab=("Hemoglobin A1c", "Hemoglobin A1c {value:.1f}%.", "Prediabetes follow-up")),
    Condition("E66.9", "Obesity, unspecified", "Obesity", 18,
              "Discussed weight history and patient-defined functional goals.",
              "Review agreed health and activity goals"),
    Condition("F32.A", "Depression, unspecified depression type", "Depression", 18,
              "Discussed mood, sleep, daily functioning and supports.",
              "Review functioning and mood at follow-up",
              referral=("Behavioral health", "Discuss ongoing support")),
    Condition("L30.9", "Dermatitis, unspecified", "Dermatitis", 18,
              "Reports intermittent pruritic skin patches; reviewed exposure history.",
              "Review skin symptoms and documented triggers"),
    Condition("G56.01", "Carpal tunnel syndrome, right upper limb", "Right carpal tunnel syndrome", 25,
              "Reports intermittent right hand paresthesias during repetitive tasks.",
              "Review hand symptoms and functional limitations"),
    Condition("M81.0", "Age-related osteoporosis without current pathological fracture", "Age-related osteoporosis", 65,
              "Reviewed previous bone density testing and fall history.",
              "Review bone health and functional safety"),
    Condition("K76.0", "Fatty (change of) liver, not elsewhere classified", "Hepatic steatosis", 35,
              "Reviewed prior liver imaging and laboratory history.",
              "Review prior liver assessment and interval laboratory results"),
    Condition("K58.9", "Irritable bowel syndrome without diarrhea", "Irritable bowel syndrome without diarrhea", 18,
              "Reports intermittent abdominal discomfort and variable bowel habits.",
              "Review symptom diary and functional impact"),
)

HISTORICAL_MEDICATIONS = {
    "I10": ("Lisinopril", "10 mg", "oral", "Daily", "Previous medication stopped after persistent cough."),
    "E78.5": ("Atorvastatin", "10 mg", "oral", "Nightly", "Previous strength replaced at medication review."),
    "K21.9": ("Famotidine", "20 mg", "oral", "Daily as needed", "Previous regimen changed after symptom review."),
    "F41.9": ("Escitalopram", "5 mg", "oral", "Daily", "Previous medication stopped after reported intolerance."),
}

VISIT_DETAILS = {
    "I10": ("Home readings vary with schedule; no new symptoms reported.",
            "Brought several home readings but some dates are missing.",
            "Reviewed difficulty keeping a consistent home measurement routine."),
    "E11.9": ("Glucose log is incomplete on busy days.",
              "Reports that meal timing varies; discussed recorded readings.",
              "Brought interval glucose records and questions about their variation."),
    "M17.11": ("Stairs and prolonged standing remain difficult; shorter walks are better tolerated.",
               "Reports morning stiffness and limits on longer walks.",
               "Discussed variable knee discomfort during usual household activities."),
    "M54.50": ("Back symptoms vary with prolonged sitting and activity.",
               "Discussed limits on bending and lifting during daily tasks.",
               "Reports intermittent flares with longer periods of standing."),
    "G43.909": ("Reviewed headache diary; timing varies with sleep and daily routine.",
                "Reports intermittent headaches that interfere with some planned activities.",
                "Discussed prior headache episodes and changes in their frequency."),
    "G47.33": ("Reports variable sleep quality and questions about equipment comfort.",
               "Discussed the practical barriers to maintaining the sleep routine.",
               "Reviewed reported device use and daytime symptoms."),
    "F41.9": ("Reports stress around changing daily responsibilities; discussed supports.",
              "Sleep and concentration vary during stressful periods.",
              "Reviewed which daily activities are most affected by symptoms."),
    "K21.9": ("Symptoms vary with meal timing and lying down after meals.",
              "Reviewed intermittent symptoms and the previous medication history.",
              "Reports fewer symptoms on some days; discussed the symptom diary."),
}


def _add_complexity(chart: "Chart", rng: Random) -> None:
    existing = {condition.code for condition in chart.conditions}
    active_count = len(existing - {"J06.9"})
    if active_count >= 4:
        return
    bmi = chart.weight / (chart.height / 100) ** 2
    eligible = []
    for condition in ADDITIONAL_CONDITIONS:
        if chart.age < condition.minimum_age:
            continue
        if condition.code == "R73.03" and ("E11.9" in existing or bmi < 25):
            continue
        if condition.code == "E66.9" and bmi < 30:
            continue
        if condition.code == "K76.0" and not (bmi >= 30 or "E11.9" in existing):
            continue
        eligible.append(condition)
    if eligible and rng.random() < (.57 if active_count else .22):
        chosen = rng.choice(eligible)
        chart.conditions.append(chosen)


@dataclass
class Chart:
    patient: Patient
    age: int
    conditions: list[Condition]
    height: float
    weight: float
    visits: list[Appointment] = field(default_factory=list)
    problems: list[Problem] = field(default_factory=list)


def _age(rng: Random) -> int:
    band = rng.choices([(18, 29), (30, 44), (45, 64), (65, 79), (80, 94)],
                       weights=[17, 26, 31, 21, 5])[0]
    return rng.randint(*band)


def _dob(age: int, as_of: date, rng: Random) -> date:
    # A birthday in the preceding 365-day window gives the selected age exactly,
    # without constructing invalid February 29 dates.
    birth = date(as_of.year - age, rng.randint(1, 12), rng.randint(1, 28))
    if (birth.month, birth.day) > (as_of.month, as_of.day):
        birth = birth.replace(year=birth.year - 1)
    return birth


def _conditions(age: int, rng: Random) -> list[Condition]:
    counts = [0, 1, 2, 3, 4]
    weights = ([52, 32, 13, 3, 0] if age < 30 else
               [34, 36, 22, 7, 1] if age < 45 else
               [19, 32, 30, 15, 4] if age < 65 else
               [8, 22, 34, 25, 11])
    count = rng.choices(counts, weights=weights)[0]
    eligible = [c for c in CONDITIONS[:-1] if age >= c.minimum_age]
    selected = []
    for _ in range(count):
        weights = [3 if age >= 50 and c.code in ("I10", "E78.5", "E11.9", "M17.11") else 1
                   for c in eligible]
        chosen = rng.choices(eligible, weights=weights)[0]
        selected.append(chosen)
        eligible.remove(chosen)
    # A resolved episode provides a historical problem without asserting an active illness.
    if rng.random() < .23:
        selected.append(CONDITIONS[-1])
    return selected


def _chart(patient: Patient, age: int, rng: Random) -> Chart:
    height = round(min(199, max(145, rng.gauss(169, 10))), 1)
    bmi = min(43, max(18, rng.gauss(27.5 if age >= 40 else 25.5, 5)))
    return Chart(patient, age, _conditions(age, rng), height,
                 round(bmi * (height / 100) ** 2, 1))


def _timestamp(day: date, hour: int = 16) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=timezone.utc)


def _snapshot(problem: Problem) -> dict:
    return dict(problem_id=problem.id, problem_name=problem.name,
                icd10_code=problem.icd10_code, icd10_release=problem.icd10_release)


def _result(code: str, template: str, rng: Random) -> str:
    bounds = {
        "I10": (.65, 1.25), "E78.5": (78, 172), "E11.9": (6.1, 8.6),
        "E03.9": (.8, 5.8), "D50.9": (10.2, 12.4), "E55.9": (14, 29),
        "R73.03": (5.7, 6.4),
    }
    return template.format(value=rng.uniform(*bounds[code]))


def add_clinic_population(session: Session, *, as_of: date,
                          total: int = POPULATION_SIZE,
                          reference_patients: tuple[Patient, ...] = ()) -> None:
    """Add charts to a fresh seed transaction; caller owns commit/rollback.

    Reference patients are already inserted. Optional sparse reference charts
    (Maria and Devin) receive history without replacing their existing records.
    """
    if not REFERENCE_PATIENTS <= total <= POPULATION_SIZE:
        raise ValueError("Unsupported synthetic population size")
    if total == REFERENCE_PATIENTS:
        return

    rng = Random(SEED)
    names = set()
    charts = []
    for _ in range(total - REFERENCE_PATIENTS):
        age = _age(rng)
        sex = rng.choices(["female", "male", "unknown", "intersex"],
                          weights=[48, 48, 3, 1])[0]
        if sex in ("female", "male"):
            usual = "she/her" if sex == "female" else "he/him"
            alternate = "he/him" if sex == "female" else "she/her"
            pronouns = rng.choices([usual, alternate, "they/them", None],
                                  weights=[90, 2, 5, 3])[0]
        else:
            pronouns = rng.choice(["she/her", "he/him", "they/them", None])
        # Mix conventionally gendered and gender-neutral names. A name is
        # never used as a clinical input.
        neutral = FIRST_NAMES[FIRST_NAMES.index("Alex"):]
        if pronouns == "she/her":
            candidates = FIRST_NAMES[:FIRST_NAMES.index("Adrian")] + neutral
        elif pronouns == "he/him":
            candidates = FIRST_NAMES[FIRST_NAMES.index("Adrian"):]
        else:
            candidates = FIRST_NAMES
        while True:
            first, last = rng.choice(candidates), rng.choice(LAST_NAMES)
            if (first, last) not in names:
                names.add((first, last))
                break
        # Preserve individual variation while avoiding an automatic clinical
        # inference from a person's name or pronouns.
        patient = Patient(first_name=first, last_name=last, date_of_birth=_dob(age, as_of, rng),
                          sex_at_birth=sex, pronouns=pronouns)
        charts.append(_chart(patient, age, rng))
    session.add_all([chart.patient for chart in charts])
    session.flush()
    for patient in reference_patients:
        age = as_of.year - patient.date_of_birth.year - (
            (as_of.month, as_of.day) < (patient.date_of_birth.month, patient.date_of_birth.day))
        charts.append(_chart(patient, age, rng))

    # A separate random stream preserves the original generated identities.
    complexity = Random(SEED + 71)
    for chart in charts:
        _add_complexity(chart, complexity)

    # Batch by dependency layer instead of flushing on every record.
    for i, chart in enumerate(charts):
        patient_id = chart.patient.id
        visit_count = rng.choices([1, 2, 3, 4], [22, 44, 26, 8])[0]
        # Eight non-overlapping slots per historical clinic day; separate
        # 180-day bands prevent overlapping historical visits.
        latest = as_of - timedelta(days=35 + i // 8)
        slot = time(8 + i % 8)
        for j in range(visit_count - 1, -1, -1):
            day = latest - timedelta(days=180 * j)
            active = [c for c in chart.conditions if c.code != "J06.9"]
            reason = (active[0].name + " follow-up" if active and j == 0
                      else "Routine primary care review" if j else "Preventive visit")
            chart.visits.append(Appointment(patient_id=patient_id, scheduled_date=day,
                                            start_time=slot, duration_minutes=30,
                                            reason_for_visit=reason, status="completed"))
        for condition in chart.conditions:
            resolved = condition.code == "J06.9"
            onset = (latest - timedelta(days=12) if resolved else
                     chart.visits[0].scheduled_date - timedelta(days=rng.randint(45, 700)))
            chart.problems.append(Problem(patient_id=patient_id, name=condition.name,
                                          icd10_code=condition.code, icd10_title=condition.title,
                                          icd10_release=CODE_RELEASE,
                                          status="resolved" if resolved else "active",
                                          onset_date=onset,
                                          resolved_date=latest - timedelta(days=3) if resolved else None))
        session.add_all(chart.visits + chart.problems)
        if rng.random() < .19:
            allergen, reaction, severity = rng.choice([
                ("Penicillin", "Rash", "moderate"), ("Latex", "Hives", "moderate"),
                ("Adhesive tape", "Local skin irritation", "mild"),
                ("Shellfish", "Hives", "moderate"), ("Nickel", "Contact rash", "mild"),
            ])
            # Do not duplicate the fixed Maria allergy.
            if chart.patient.first_name != "Maria":
                session.add(Allergy(patient_id=patient_id, allergen=allergen, reaction=reaction,
                                    severity=severity, status="active",
                                    onset_date=latest - timedelta(days=30)))

    session.flush()
    encounters = []
    goals = []
    upcoming = []
    for i, chart in enumerate(charts):
        patient_id = chart.patient.id
        active = [(c, p) for c, p in zip(chart.conditions, chart.problems) if p.status == "active"]
        hypertensive = any(c.code == "I10" for c, _ in active)
        history_rng = Random(SEED + chart.patient.id * 31)
        employment, barrier = daily_context(chart.patient, as_of)
        for c, problem in active:
            if c.medication and rng.random() < .82:
                name, dose, route, frequency = c.medication
                session.add(Medication(patient_id=patient_id, name=name, strength=dose,
                                       dose=dose, route=route, frequency=frequency, status="active",
                                       start_date=chart.visits[0].scheduled_date,
                                       indications=[MedicationIndication(**_snapshot(problem))]))
                if c.code in HISTORICAL_MEDICATIONS and history_rng.random() < .35:
                    name, dose, route, frequency, reason = HISTORICAL_MEDICATIONS[c.code]
                    end = chart.visits[0].scheduled_date - timedelta(days=1)
                    start_date = max(problem.onset_date, end - timedelta(days=60))
                    session.add(Medication(patient_id=patient_id, name=name, strength=dose,
                                           dose=dose, route=route, frequency=frequency,
                                           status="discontinued", start_date=start_date, end_date=end,
                                           instructions=reason,
                                           indications=[MedicationIndication(**_snapshot(problem))]))
        for j, appointment in enumerate(chart.visits):
            day = appointment.scheduled_date
            # Relative event times preserve ordering around the clinic-local
            # appointment; synthetic UTC offset is fixed for this dataset.
            start = datetime.combine(day, appointment.start_time, tzinfo=timezone.utc) + timedelta(hours=5)
            stamp = start + timedelta(minutes=30)
            for prior, status, at in (
                (None, "scheduled", start - timedelta(days=14)),
                ("scheduled", "checked_in", start - timedelta(minutes=5)),
                ("checked_in", "completed", stamp),
            ):
                session.add(AppointmentStatusChange(appointment_id=appointment.id,
                            previous_status=prior, new_status=status, changed_at=at))
            sbp = rng.randint(128, 154) if hypertensive else rng.randint(104, 132)
            dbp = rng.randint(76, 94) if hypertensive else rng.randint(60, 82)
            weight = round(max(43, chart.weight + rng.uniform(-2, 2)), 1)
            pulse = rng.randint(59, 91)
            session.add(Vital(patient_id=patient_id, recorded_on=day, systolic_bp=sbp,
                              diastolic_bp=dbp, heart_rate=pulse, respiratory_rate=rng.randint(12, 18),
                              temperature_c=round(rng.uniform(36.3, 37.2), 1),
                              oxygen_saturation=rng.randint(95, 100), height_cm=chart.height,
                              weight_kg=weight))
            primary = active[j % len(active)][0] if active else None
            concerns = (primary.concern if primary else rng.choice([
                "Reviewed interval health history and current concerns.",
                "Discussed activity, sleep and routine preventive care.",
                "Reviewed home routines and questions about the health record.",
                "Reports no new concerns at this visit; reviewed interval history.",
            ]))
            if primary and primary.code in VISIT_DETAILS:
                concerns += " " + history_rng.choice(VISIT_DETAILS[primary.code])
            if j == 0:
                concerns += " " + employment
            else:
                concerns += " Compared with the previous recorded visit and reviewed interval questions."
            if j == len(chart.visits) - 1:
                concerns += " " + barrier
            assessment = ("Reviewed " + ", ".join(c.name.lower() for c, _ in active) + "."
                          if active else "Routine preventive assessment; no active problem documented.")
            if any(p.status == "resolved" and p.resolved_date <= day for p in chart.problems):
                assessment += " Prior respiratory illness resolved."
            goal_text = primary.goal if primary else "Review preventive care needs at the next visit"
            note = Encounter(patient_id=patient_id, appointment_id=appointment.id,
                             visit_date=day, reason_for_visit=appointment.reason_for_visit,
                             subjective=concerns,
                             objective=f"BP {sbp}/{dbp} mmHg, pulse {pulse} bpm, weight {weight} kg.",
                             assessment=assessment,
                             plan=goal_text + ". Reviewed follow-up and questions.",
                             patient_instructions=goal_text + ". Bring any questions to your next appointment.",
                             finalized_at=stamp)
            session.add(note)
            encounters.append((chart, note, j == len(chart.visits) - 1))
        if active and rng.random() < .25:
            goal = CareGoal(patient_id=patient_id, title=active[0][0].goal,
                            target_date=as_of + timedelta(days=rng.randint(14, 90)),
                            status="active", created_at=_timestamp(chart.visits[-1].scheduled_date))
            session.add(goal)
            goals.append((chart, goal))
        # A modest current clinic schedule plus upcoming follow-ups. Slots are
        # disjoint from the three fixed demonstration appointments.
        if i < 6 or i % 4 == 0:
            day = as_of if i < 6 else as_of + timedelta(days=1 + i // 24)
            start = time(11 + i // 2, 30 * (i % 2)) if i < 6 else time(8 + (i // 4) % 6)
            reason = active[0][0].name + " follow-up" if active else "Routine visit"
            appointment = Appointment(patient_id=patient_id, scheduled_date=day,
                                      start_time=start, duration_minutes=30,
                                      reason_for_visit=reason, status="scheduled")
            session.add(appointment)
            upcoming.append(appointment)

    session.flush()
    orders = []
    for chart, note, latest in encounters:
        for problem in chart.problems:
            if problem.onset_date <= note.visit_date and (
                    problem.status == "active" or problem.resolved_date <= note.visit_date):
                session.add(EncounterProblem(encounter_id=note.id, problem_id=problem.id,
                            problem_name_at_link=problem.name, icd10_code_at_link=problem.icd10_code,
                            icd10_release_at_link=problem.icd10_release,
                            problem_status_at_link=problem.status,
                            linked_at=note.finalized_at - timedelta(minutes=10)))
        for condition, problem in zip(chart.conditions, chart.problems):
            # Earlier monitoring provides a trajectory, not just a single result.
            # Historical tests have results; some most recent orders remain pending.
            if condition.lab and problem.onset_date <= note.visit_date and rng.random() < (.8 if latest else .4):
                name, template, reason = condition.lab
                status = rng.choices(["resulted", "ordered"], [92, 8])[0] if latest else "resulted"
                order = LabOrder(encounter_id=note.id, test_name=name, priority="routine",
                                 clinical_reason=reason, status=status,
                                 ordered_at=note.finalized_at - timedelta(minutes=10),
                                 indications=[LabOrderIndication(**_snapshot(problem))])
                session.add(order)
                if status == "resulted":
                    orders.append((order, note.visit_date, _result(condition.code, template, rng)))
            if latest and condition.referral and rng.random() < .18:
                specialty, reason = condition.referral
                session.add(Referral(encounter_id=note.id, specialty=specialty, reason=reason,
                                     priority="routine", status="requested",
                                     requested_at=note.finalized_at - timedelta(minutes=10)))
    for chart, goal in goals:
        day = chart.visits[-1].scheduled_date
        session.add(CareGoalProgress(goal_id=goal.id, note="Discussed goal and planned follow-up.",
                                     recorded_at=_timestamp(day)))
        if rng.random() < .55:
            session.add(FollowUpTask(patient_id=chart.patient.id, care_goal_id=goal.id,
                                     title=goal.title, due_date=goal.target_date, status="open",
                                     created_at=_timestamp(day)))
    for appointment in upcoming:
        session.add(AppointmentStatusChange(appointment_id=appointment.id, previous_status=None,
                                             new_status="scheduled", changed_at=_timestamp(as_of, 7)))
    session.flush()
    for order, day, result in orders:
        reported = _timestamp(day + timedelta(days=1))
        session.add(LabResult(lab_order_id=order.id, collected_on=day, result_text=result,
                              reported_at=reported,
                              released_at=reported + timedelta(hours=1) if rng.random() < .9 else None))
    seed_chart_backgrounds(session, as_of=as_of)


def extend_browser_population() -> None:
    """Extend only the fixed, freshly created tab-local demonstration dataset."""
    import sys
    from backend.database import engine

    if sys.platform != "emscripten" or engine.dialect.name != "sqlite" or engine.url.database not in (None, "", ":memory:"):
        raise RuntimeError("Population extension is restricted to the browser demo")
    with Session(engine) as session:
        patients = session.scalars(select(Patient).order_by(Patient.id)).all()
        if [(p.first_name, p.last_name) for p in patients] != [
            ("Jordan", "Lee"), ("Maria", "Thompson"), ("Devin", "Brooks")
        ]:
            raise RuntimeError("Expected the original three reference charts")
        add_clinic_population(session, as_of=date.today(), reference_patients=tuple(patients[1:]))
        if session.scalar(select(func.count()).select_from(Patient)) != POPULATION_SIZE:
            raise RuntimeError("Synthetic patient population did not initialize")
        session.commit()
