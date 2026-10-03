from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import engine
from backend.models import Patient

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Primary Care EMR API"}

@app.get("/patients")
def read_patients():
    with Session(engine) as session:
        patients = session.scalars(
            select(Patient).order_by(
                Patient.last_name,
                Patient.first_name,
                Patient.date_of_birth,
            )
        ).all()

        return [
            {
                "id": patient.id,
                "first_name": patient.first_name,
                "middle_name": patient.middle_name,
                "last_name": patient.last_name,
                "suffix": patient.suffix,
                "date_of_birth": patient.date_of_birth,
                "pronouns": patient.pronouns,
                "sex_at_birth": patient.sex_at_birth,
            }
            for patient in patients
        ]