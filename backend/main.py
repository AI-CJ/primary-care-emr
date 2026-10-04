from fastapi import FastAPI, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.database import engine
from backend.models import Patient
from backend.schemas import PatientCreate
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Primary Care EMR API"}

@app.get("/patients")
def read_patients(search: str | None = None):
    with Session(engine) as session:
        query = select(Patient)

        if search:
            search_term = f"%{search.strip()}%"

            query = query.where(
                or_(
                    Patient.first_name.ilike(search_term),
                    Patient.middle_name.ilike(search_term),
                    Patient.last_name.ilike(search_term),
                )
            )

        patients = session.scalars(
            query.order_by(
                Patient.last_name,
                Patient.first_name,
                Patient.date_of_birth,
            )
        ).all()

        return [
            {
                "id": patient.id,
                "first_name": patient.first_name,
                "preferred_name": patient.preferred_name,
                "middle_name": patient.middle_name,
                "last_name": patient.last_name,
                "suffix": patient.suffix,
                "date_of_birth": patient.date_of_birth,
                "pronouns": patient.pronouns,
                "custom_pronouns": patient.custom_pronouns,
                "sex_at_birth": patient.sex_at_birth,
            }
            for patient in patients
        ]

@app.post("/patients", status_code=201)
def create_patient(patient_data: PatientCreate):
    patient = Patient(
        first_name=patient_data.first_name,
        preferred_name=patient_data.preferred_name,
        middle_name=patient_data.middle_name,
        last_name=patient_data.last_name,
        suffix=patient_data.suffix,
        date_of_birth=patient_data.date_of_birth,
        pronouns=patient_data.pronouns,
        custom_pronouns=patient_data.custom_pronouns,
        sex_at_birth=patient_data.sex_at_birth,
    )

    with Session(engine) as session:
        session.add(patient)
        session.commit()
        session.refresh(patient)

        return {
            "id": patient.id,
            "first_name": patient.first_name,
            "preferred_name": patient.preferred_name,
            "middle_name": patient.middle_name,
            "last_name": patient.last_name,
            "suffix": patient.suffix,
            "date_of_birth": patient.date_of_birth,
            "pronouns": patient.pronouns,
            "custom_pronouns": patient.custom_pronouns,
            "sex_at_birth": patient.sex_at_birth,
        }

@app.get("/patients/{patient_id}")
def read_patient(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        return {
            "id": patient.id,
            "first_name": patient.first_name,
            "preferred_name": patient.preferred_name,
            "middle_name": patient.middle_name,
            "last_name": patient.last_name,
            "suffix": patient.suffix,
            "date_of_birth": patient.date_of_birth,
            "pronouns": patient.pronouns,
            "custom_pronouns": patient.custom_pronouns,
            "sex_at_birth": patient.sex_at_birth,
        }