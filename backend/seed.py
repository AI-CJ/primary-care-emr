from datetime import date

from sqlalchemy.orm import Session

from backend.database import engine
from backend.models import Patient
from sqlalchemy import select

patients = [
    Patient(
        first_name="Jordan",
        last_name="Lee",
        date_of_birth=date(1984, 3, 12),
    ),
    Patient(
        first_name="Maria",
        last_name="Thompson",
        date_of_birth=date(1957, 8, 24),
    ),
    Patient(
        first_name="Devin",
        last_name="Brooks",
        date_of_birth=date(2001, 11, 5),
    ),
]


with Session(engine) as session:
    existing_patient = session.scalar(select(Patient.id).limit(1))

    if existing_patient is not None:
        print("Seed data already exists; skipping.")
    else:
        session.add_all(patients)
        session.commit()
        print("Seeded 3 synthetic patients.")