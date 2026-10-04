from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.database import engine
from backend.models import Patient
from backend.schemas import PatientCreate, PatientRead


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Primary Care EMR API"}


@app.get(
    "/patients",
    response_model=list[PatientRead],
)
def read_patients(search: str | None = None):
    query = select(Patient)

    if search and search.strip():
        search_term = f"%{search.strip()}%"

        query = query.where(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.preferred_name.ilike(search_term),
                Patient.middle_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
            )
        )

    query = query.order_by(
        Patient.last_name,
        Patient.first_name,
        Patient.date_of_birth,
    )

    with Session(engine) as session:
        patients = session.scalars(query).all()

        return list(patients)


@app.post(
    "/patients",
    response_model=PatientRead,
    status_code=201,
)
def create_patient(patient_data: PatientCreate):
    patient = Patient(
        **patient_data.model_dump()
    )

    with Session(engine) as session:
        session.add(patient)
        session.commit()
        session.refresh(patient)

        return patient


@app.put(
    "/patients/{patient_id}",
    response_model=PatientRead,
)
def update_patient(
    patient_id: int,
    patient_data: PatientCreate,
):
    with Session(engine) as session:
        patient = session.get(
            Patient,
            patient_id,
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        for field, value in patient_data.model_dump().items():
            setattr(patient, field, value)

        session.commit()
        session.refresh(patient)

        return patient


@app.get(
    "/patients/{patient_id}",
    response_model=PatientRead,
)
def read_patient(patient_id: int):
    with Session(engine) as session:
        patient = session.get(
            Patient,
            patient_id,
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        return patient