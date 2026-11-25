"""Seed documented fictional immunizations and reconcile known demo ingredients.

A small build-generated reference snapshot is used so the complete drug
catalog never has to be loaded on the login path. Dates model historical
documentation, not recommendations or a forecast of immunizations due.
"""
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from random import Random

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from backend.models import Immunization, Medication, Patient

SEED_REFERENCE_PATH = Path(__file__).resolve().parent / "data" / "seed-reference.json"
MEDICATION_NAMES = {
    "amlodipine", "atorvastatin", "metformin", "levothyroxine",
    "budesonide", "cetirizine", "omeprazole", "sertraline",
    "lisinopril", "famotidine", "escitalopram",
}
VACCINE_CODES = {"88", "115", "187", "216", "45", "208", "207"}
MANUFACTURER_CODES = {"PFR", "MOD"}


def _age(patient, day):
    return day.year - patient.date_of_birth.year - (
        (day.month, day.day) < (patient.date_of_birth.month, patient.date_of_birth.day))


def seed_vaccination_history(session: Session, *, as_of: date):
    session.flush()
    # A real catalog is required for the full fictional seed; never invent a
    # missing RxCUI or CVX title, and never overwrite existing patient charts.
    if not SEED_REFERENCE_PATH.is_file():
        raise RuntimeError("Prepare the official medication and vaccine catalogs before seeding.")
    references = json.loads(SEED_REFERENCE_PATH.read_text(encoding="utf-8"))
    rx, cvx, mvx = (references[key] for key in ("rxnorm", "cvx", "mvx"))
    codes = {item["code"]: item for item in cvx["rows"]}
    manufacturers = {item["code"]: item for item in mvx["rows"]}
    ingredients = {item["name"].casefold(): item for item in rx["rows"]}
    if not VACCINE_CODES <= codes.keys() or not MANUFACTURER_CODES <= manufacturers.keys():
        raise RuntimeError("Incomplete seed terminology snapshot")

    updates = []
    for medication_id, name in session.execute(select(Medication.id, Medication.name)):
        item = ingredients.get(name.casefold())
        if item:
            updates.append(dict(id=medication_id, rxnorm_cui=item["code"],
                                rxnorm_kind=item["kind"], rxnorm_release=rx["release"]))
    if updates:
        session.execute(update(Medication), updates)

    records = []
    for patient in session.scalars(select(Patient).order_by(Patient.id)):
        rng = Random(165047 + patient.id)
        reference = (patient.first_name, patient.last_name) == ("Jordan", "Lee")
        seen = set()

        def add(code, day, *, source="historical_record", dose=None, manufacturer=None, route=None):
            if not patient.date_of_birth <= day <= as_of or (code, day) in seen:
                return
            seen.add((code, day))
            entry = codes[code]
            maker = manufacturers.get(manufacturer)
            records.append(dict(
                patient_id=patient.id, cvx_code=entry["code"], vaccine_name=entry["name"],
                cvx_release=cvx["release"], administered_on=day, source=source,
                manufacturer_code=maker["code"] if maker else None,
                manufacturer_name=maker["name"] if maker else None,
                mvx_release=mvx["release"] if maker else None, dose_number=dose,
                route=route, lot_number=None, site=None,
                notes="Previous vaccination history reviewed; lot and site not available.",
                recorded_at=datetime.combine(as_of, datetime.min.time(), tzinfo=timezone.utc),
            ))

        # Some patients have sparse records; absence of documentation is not
        # evidence of absent vaccination or a clinical indication.
        if not reference and rng.random() < .10:
            continue
        for year in range(max(2021, as_of.year - 4), as_of.year + 1):
            day = date(year, rng.choice([9, 10, 11]), rng.randint(1, 25))
            if reference and year == as_of.year:
                day = min(day, as_of)
                add("88", day)
            elif rng.random() < .53:
                add("88", day, source=rng.choice(["historical_record", "patient_reported"]))

        day = date(max(2016, as_of.year - rng.randint(1, 9)), rng.randint(1, 12), rng.randint(1, 28))
        if _age(patient, day) >= 11 and (reference or rng.random() < .73):
            add("115", day, route="Intramuscular")

        # Original formulations are used only on historical dates, not as
        # current products. A recorded series may be incomplete.
        if as_of >= date(2022, 4, 1) and _age(patient, date(2021, 6, 1)) >= 18 and rng.random() < .68:
            first = date(2021, 3, 1) + timedelta(days=rng.randint(0, 300))
            code, maker, interval = rng.choice([("208", "PFR", 21), ("207", "MOD", 28)])
            add(code, first, dose=1, manufacturer=maker, route="Intramuscular")
            if rng.random() < .86:
                add(code, first + timedelta(days=interval + rng.randint(0, 10)), dose=2,
                    manufacturer=maker, route="Intramuscular")

        zoster_day = as_of - timedelta(days=rng.randint(240, 1600))
        if zoster_day >= date(2018, 1, 1) and _age(patient, zoster_day) >= 50 and rng.random() < .55:
            add("187", zoster_day, dose=1, route="Intramuscular")
            if rng.random() < .76:
                add("187", zoster_day + timedelta(days=rng.randint(65, 170)), dose=2, route="Intramuscular")

        pneumo_day = as_of - timedelta(days=rng.randint(50, 800))
        if pneumo_day >= date(2023, 3, 9) and _age(patient, pneumo_day) >= 65 and rng.random() < .65:
            add("216", pneumo_day, route="Intramuscular")

        hep_day = as_of - timedelta(days=rng.randint(400, 1700))
        if _age(patient, hep_day) >= 18 and rng.random() < .32:
            # Historical formulation not known; do not guess the manufacturer
            # or dose number from an incomplete external record.
            add("45", hep_day)

    if records:
        session.execute(insert(Immunization), records)
