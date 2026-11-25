"""Original fictional longitudinal histories and prior imaging reports.

The authored cases are for software verification, not clinical recommendations.
Imaging is selective and has a documented reason, result and chronology.
"""
from collections import defaultdict
from datetime import date, timedelta
from random import Random

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from backend.models import Encounter, ImagingReport, Medication, Patient, PatientBackground, Problem

CONTEXT_SEED = 842016

# Individual circumstances are independent of name, ethnicity and gender.
WORK_CONTEXTS = (
    ("Works early warehouse shifts.", "Breakfast and medication routines vary on workdays."),
    ("Works remotely in an administrative role.", "Prolonged sitting and scheduling breaks were discussed."),
    ("Works in retail with changing shifts.", "Prefers appointments that fit the weekly rota."),
    ("Works in education.", "Visit scheduling is easier during school breaks."),
    ("Works in food service.", "Irregular meal breaks sometimes disrupt the daily routine."),
    ("Self-employed in a skilled trade.", "Time away from work is a practical barrier to follow-up."),
    ("Works part-time.", "Can attend morning appointments most weeks."),
    ("Currently not employed.", "Prefers a clear written plan and predictable appointment times."),
)
RETIRED_CONTEXTS = (
    ("Retired and lives independently.", "Keeps a written medication list and prefers morning visits."),
    ("Retired; helps care for a family member.", "May need to coordinate transportation and appointments."),
    ("Retired and volunteers locally.", "Wants a follow-up plan that supports usual activities."),
    ("Retired and shares a household with family.", "Family support is available when requested."),
)
ACTIVITY = (
    "Walks regularly when the weather permits.",
    "Activity varies with work demands.",
    "Enjoys gardening and light household activities.",
    "Reports a largely sedentary routine.",
    "Uses a stationary bicycle when time allows.",
    "Walks with a friend on weekends.",
)
FAMILY = (
    "Mother has hypertension; other first-degree history not established.",
    "Father developed type 2 diabetes in later adulthood.",
    "One sibling has asthma; parents' medical histories are incompletely known.",
    "Maternal history of thyroid disease; no further details available.",
    "Reports a parent with coronary artery disease in later life.",
    "No significant first-degree history reported at the last review.",
    "Family medical history is incomplete; patient is gathering more information.",
    "A first-degree relative has osteoarthritis; other details not recorded.",
)
TOBACCO = ("Never smoked.", "Former tobacco use reported; quit several years ago.",
           "Current cigarette use reported; duration not fully documented.",
           "Tobacco use was not established at this review.")
ALCOHOL = ("Reports no alcohol use.", "Reports occasional alcohol use.",
           "Reports one or two drinks on some weekends.",
           "Alcohol history was not established at this review.")
LIVING = ("Lives alone.", "Shares a home with a partner.",
          "Lives with family members.", "Shares housing with a friend.",
          "Lives independently; a friend assists when needed.")
FOLLOW_UP = (
    "Prefers written instructions and time to review results before the next visit.",
    "Requests a concise explanation of results and a clear follow-up date.",
    "Uses a paper calendar to track appointments.",
    "Prefers to discuss medication changes before they are made.",
    "Wants care plans to focus on daily functioning and manageable steps.",
    "Reports difficulty attending appointments without advance notice.",
    "Would like the next visit to include review of unresolved questions.",
    "Prefers the portal for reviewing shared test reports.",
)

# The following describes prior events, not active problems or new orders.
# Each event includes a corresponding report only when imaging formed part of
# that documented historical episode.
PRIOR_EVENTS = (
    ("Remote appendicitis resolved after surgery.",
     "Appendectomy; patient recalls an uncomplicated recovery.",
     None),
    ("Prior gallstone-related abdominal pain resolved after surgery.",
     "Laparoscopic cholecystectomy; no persistent symptoms reported.",
     ("Ultrasound", "Right upper quadrant ultrasound", "Prior post-meal right upper abdominal pain.",
      "Mobile shadowing gallstones in the gallbladder. No gallbladder wall thickening or biliary ductal dilation.",
      "Cholelithiasis; no sonographic evidence of acute cholecystitis.")),
    ("Remote wrist fracture after a fall; healed without persistent limitation.",
     "No operative treatment reported for the wrist injury.",
     ("Radiograph", "Wrist radiographs", "Prior fall with focal wrist pain and swelling.",
      "Nondisplaced distal radius fracture with preserved alignment.",
      "Nondisplaced distal radius fracture.")),
    ("Previous community-acquired pneumonia; completed treatment and recovered.",
     "No surgery associated with the respiratory illness.",
     ("Radiograph", "Chest radiographs", "Prior fever and productive cough.",
      "Focal right lower lobe airspace opacity. No pleural effusion or pneumothorax.",
      "Right lower lobe airspace opacity, compatible with pneumonia in the recorded clinical context.")),
    ("Remote ankle sprain; symptoms resolved after conservative care.",
     "No operation reported for the ankle injury.",
     ("Radiograph", "Ankle radiographs", "Prior twisting injury with focal bony tenderness.",
      "Lateral soft tissue swelling. Mortise alignment maintained; no acute fracture identified.",
      "Soft tissue swelling without acute osseous abnormality.")),
    ("History of symptomatic renal stone; passage documented in the outside record.",
     "No stone procedure reported.",
     ("CT", "Noncontrast CT abdomen and pelvis", "Prior acute flank pain with hematuria.",
      "Small distal ureteral calculus with mild upstream collecting system dilation.",
      "Distal ureteral stone with mild obstruction at the time of the study.")),
    ("Remote inguinal hernia repaired; no recurrent symptoms reported.",
     "Inguinal hernia repair; operative details unavailable.",
     None),
    ("Remote episode of acute gastroenteritis; symptoms resolved.",
     "No surgery associated with the episode.",
     None),
    ("Previous uncomplicated influenza-like illness; recovered.",
     "No related surgical history.",
     None),
    ("Prior cataract surgery with improved vision; follows with eye care.",
     "Cataract extraction; laterality not recorded in the primary care history.",
     None),
)

KNEE_REPORTS = (
    ("Weight-bearing right knee radiographs",
     "Persistent right knee pain with stairs and prolonged walking.",
     "Mild medial compartment joint space narrowing and marginal osteophytes. No acute fracture.",
     "Mild medial compartment osteoarthritic change."),
    ("Right knee radiographs",
     "Chronic right knee pain with activity-related stiffness.",
     "Moderate medial joint space narrowing with small tricompartmental osteophytes. No acute osseous injury.",
     "Moderate degenerative change, greatest in the medial compartment."),
    ("Weight-bearing right knee radiographs",
     "Persistent mechanical knee symptoms at prior evaluation.",
     "Medial and patellofemoral joint space narrowing. Small joint effusion; no acute fracture.",
     "Degenerative changes involving the medial and patellofemoral compartments."),
)
BACK_REPORTS = (
    ("Lumbar spine MRI without contrast",
     "Prior persistent back and intermittent leg symptoms despite a documented course of conservative care.",
     "L4-L5 disc desiccation and shallow broad-based bulge. No high-grade canal stenosis.",
     "Mild lower lumbar degenerative changes without high-grade canal narrowing."),
    ("Lumbar spine MRI without contrast",
     "Prior persistent back pain with radiating symptoms after physical therapy.",
     "L5-S1 disc height loss with a small central protrusion. No severe foraminal narrowing.",
     "L5-S1 degenerative disc change; no severe neural foraminal narrowing."),
)


def _age(patient: Patient, today: date) -> int:
    return today.year - patient.date_of_birth.year - (
        (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day))


def _report(patient_id: int, performed: date, reviewed: date, modality: str,
            study: str, indication: str, findings: str, impression: str,
            rng: Random) -> dict:
    reported = performed + timedelta(days=rng.choice([0, 0, 1, 2]))
    # Historical results are not automatically exposed to the portal.
    shared = min(reviewed, reported + timedelta(days=rng.randint(1, 7))) if rng.random() < .86 else None
    return dict(patient_id=patient_id, performed_on=performed, reported_on=reported,
                modality=modality, study=study, indication=indication,
                findings=findings, impression=impression,
                source="Prior radiology report reviewed in primary care", shared_on=shared)


def seed_chart_backgrounds(session: Session, *, as_of: date) -> None:
    """Create complete fictional contexts in a fresh seed transaction only."""
    session.flush()
    if session.scalar(select(PatientBackground.patient_id).limit(1)) is not None:
        raise ValueError("Background seed requires an empty history table")

    problems = defaultdict(list)
    medications = defaultdict(list)
    visits = defaultdict(list)
    for row in session.scalars(select(Problem).order_by(Problem.id)):
        problems[row.patient_id].append(row)
    for row in session.scalars(select(Medication).order_by(Medication.id)):
        medications[row.patient_id].append(row)
    for row in session.scalars(select(Encounter).order_by(Encounter.visit_date, Encounter.id)):
        visits[row.patient_id].append(row)

    backgrounds = []
    reports = []
    for patient in session.scalars(select(Patient).order_by(Patient.id)):
        rng = Random(CONTEXT_SEED + patient.id)
        age = _age(patient, as_of)
        active = [p for p in problems[patient.id] if p.status == "active"]
        resolved = [p for p in problems[patient.id] if p.status == "resolved"]
        codes = {p.icd10_code: p for p in active}
        latest_visit = visits[patient.id][-1] if visits[patient.id] else None
        reviewed = latest_visit.visit_date if latest_visit else as_of - timedelta(days=7)
        employment, barrier = rng.choice(RETIRED_CONTEXTS if age >= 67 else WORK_CONTEXTS)
        living = rng.choice(LIVING)
        tobacco = rng.choices(TOBACCO, weights=[59, 25, 11, 5])[0]
        alcohol = rng.choices(ALCOHOL, weights=[28, 42, 25, 5])[0]
        social = " ".join((employment, living, tobacco, alcohol, rng.choice(ACTIVITY)))
        current = [m for m in medications[patient.id] if m.status == "active"]
        medical = ("Ongoing documented conditions: " + ", ".join(p.name for p in active) + "."
                   if active else "No active chronic condition documented at the last chart review.")
        if resolved:
            medical += " Historical problems: " + ", ".join(p.name for p in resolved) + "."
        if current:
            medical += " Medication list at review: " + ", ".join(
                m.name + (" " + m.strength if m.strength else "") for m in current) + "."
        else:
            medical += " No active medication entries in the reviewed record."
        surgical = rng.choice(("No prior operations reported at this review.",
                               "Past surgical history not fully established.",
                               "No previous surgery documented in the available record."))
        if rng.random() < .36:
            eligible = PRIOR_EVENTS if age >= 60 else PRIOR_EVENTS[:-1]
            event, surgery, imaging = rng.choice(eligible)
            # Keep the remote event after birth and before the reviewed encounter.
            performed = reviewed - timedelta(days=rng.randint(210, min(2200, max(210, (age - 15) * 365))))
            medical += " " + event + " Prior episode dated approximately " + str(performed.year) + "."
            surgical = surgery + " History obtained at the primary care review."
            if imaging:
                reports.append(_report(patient.id, performed, reviewed, *imaging, rng))
        if "M17.11" in codes and rng.random() < .78:
            study, indication, findings, impression = rng.choice(KNEE_REPORTS)
            onset = codes["M17.11"].onset_date or reviewed - timedelta(days=90)
            performed = min(reviewed - timedelta(days=21), onset + timedelta(days=rng.randint(14, 45)))
            reports.append(_report(patient.id, performed, reviewed, "Radiograph", study,
                                   indication, findings, impression, rng))
            medical += " Prior right knee films are available; symptoms affect prolonged walking."
        if "M54.50" in codes and rng.random() < .27:
            study, indication, findings, impression = rng.choice(BACK_REPORTS)
            onset = codes["M54.50"].onset_date or reviewed - timedelta(days=120)
            performed = min(reviewed - timedelta(days=10), onset + timedelta(days=90))
            reports.append(_report(patient.id, performed, reviewed, "MRI", study,
                                   indication, findings, impression, rng))
            medical += " A prior course of conservative back care is documented; prior MRI was reviewed."
        family = rng.choice(FAMILY)
        care = barrier + " " + rng.choice(FOLLOW_UP)
        if "I10" in codes:
            care += " Home blood pressure recording is part of the existing follow-up discussion."
        if "E11.9" in codes:
            care += " Meal timing and the glucose record are part of the ongoing review."
        if "M17.11" in codes or "M54.50" in codes:
            care += " Activity tolerance and functional limitations are important to the patient's goals."
        backgrounds.append(dict(patient_id=patient.id, reviewed_on=reviewed,
                                medical_history=medical, surgical_history=surgical,
                                family_history=family, social_history=social, care_context=care))

    # Bulk insert the small read-only history records, rather than introducing
    # one database round trip per chart.
    session.execute(insert(PatientBackground), backgrounds)
    if reports:
        session.execute(insert(ImagingReport), reports)
