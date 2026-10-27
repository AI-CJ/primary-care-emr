from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.database import engine
from backend.scheduling import ensure_appointment_slot_open
from backend.models import Allergy, Appointment, Encounter, Medication, Patient, Problem, Vital
from backend.schemas import (
    AllergyCreate,
    AllergyRead,
    AppointmentCreate,
    AppointmentRead,
    EncounterCreate,
    EncounterRead,
    MedicationCreate,
    MedicationRead,
    PatientCreate,
    PatientRead,
    ProblemCreate,
    ProblemRead,
    VitalCreate,
    VitalRead,
)


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
    patient = Patient(**patient_data.model_dump())

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
        patient = session.get(Patient, patient_id)

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
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        return patient


@app.get(
    "/patients/{patient_id}/problems",
    response_model=list[ProblemRead],
)
def read_patient_problems(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        query = (
            select(Problem)
            .where(Problem.patient_id == patient_id)
            .order_by(Problem.status, Problem.name)
        )

        problems = session.scalars(query).all()
        return list(problems)


@app.post(
    "/patients/{patient_id}/problems",
    response_model=ProblemRead,
    status_code=201,
)
def create_patient_problem(
    patient_id: int,
    problem_data: ProblemCreate,
):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        problem = Problem(
            patient_id=patient_id,
            **problem_data.model_dump(),
        )

        session.add(problem)
        session.commit()
        session.refresh(problem)
        return problem


@app.put(
    "/problems/{problem_id}",
    response_model=ProblemRead,
)
def update_problem(
    problem_id: int,
    problem_data: ProblemCreate,
):
    with Session(engine) as session:
        problem = session.get(Problem, problem_id)

        if problem is None:
            raise HTTPException(
                status_code=404,
                detail="Problem not found",
            )

        for field, value in problem_data.model_dump().items():
            setattr(problem, field, value)

        session.commit()
        session.refresh(problem)
        return problem


@app.get(
    "/patients/{patient_id}/medications",
    response_model=list[MedicationRead],
)
def read_patient_medications(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        query = (
            select(Medication)
            .where(Medication.patient_id == patient_id)
            .order_by(Medication.status, Medication.name)
        )

        medications = session.scalars(query).all()
        return list(medications)


@app.post(
    "/patients/{patient_id}/medications",
    response_model=MedicationRead,
    status_code=201,
)
def create_patient_medication(
    patient_id: int,
    medication_data: MedicationCreate,
):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        medication = Medication(
            patient_id=patient_id,
            **medication_data.model_dump(),
        )

        session.add(medication)
        session.commit()
        session.refresh(medication)
        return medication


@app.put(
    "/medications/{medication_id}",
    response_model=MedicationRead,
)
def update_medication(
    medication_id: int,
    medication_data: MedicationCreate,
):
    with Session(engine) as session:
        medication = session.get(Medication, medication_id)

        if medication is None:
            raise HTTPException(
                status_code=404,
                detail="Medication not found",
            )

        for field, value in medication_data.model_dump().items():
            setattr(medication, field, value)

        session.commit()
        session.refresh(medication)
        return medication


@app.get(
    "/patients/{patient_id}/allergies",
    response_model=list[AllergyRead],
)
def read_patient_allergies(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        query = (
            select(Allergy)
            .where(Allergy.patient_id == patient_id)
            .order_by(Allergy.status, Allergy.allergen)
        )

        allergies = session.scalars(query).all()
        return list(allergies)


@app.post(
    "/patients/{patient_id}/allergies",
    response_model=AllergyRead,
    status_code=201,
)
def create_patient_allergy(
    patient_id: int,
    allergy_data: AllergyCreate,
):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        allergy = Allergy(
            patient_id=patient_id,
            **allergy_data.model_dump(),
        )

        session.add(allergy)
        session.commit()
        session.refresh(allergy)
        return allergy


@app.put(
    "/allergies/{allergy_id}",
    response_model=AllergyRead,
)
def update_allergy(
    allergy_id: int,
    allergy_data: AllergyCreate,
):
    with Session(engine) as session:
        allergy = session.get(Allergy, allergy_id)

        if allergy is None:
            raise HTTPException(
                status_code=404,
                detail="Allergy not found",
            )

        for field, value in allergy_data.model_dump().items():
            setattr(allergy, field, value)

        session.commit()
        session.refresh(allergy)
        return allergy


@app.get(
    "/patients/{patient_id}/vitals",
    response_model=list[VitalRead],
)
def read_patient_vitals(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        query = (
            select(Vital)
            .where(Vital.patient_id == patient_id)
            .order_by(Vital.recorded_on.desc(), Vital.id.desc())
        )
        return list(session.scalars(query).all())


@app.post(
    "/patients/{patient_id}/vitals",
    response_model=VitalRead,
    status_code=201,
)
def create_patient_vital(patient_id: int, vital_data: VitalCreate):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        vital = Vital(patient_id=patient_id, **vital_data.model_dump())
        session.add(vital)
        session.commit()
        session.refresh(vital)
        return vital


@app.put(
    "/vitals/{vital_id}",
    response_model=VitalRead,
)
def update_vital(vital_id: int, vital_data: VitalCreate):
    with Session(engine) as session:
        vital = session.get(Vital, vital_id)
        if vital is None:
            raise HTTPException(status_code=404, detail="Vitals record not found")

        for field, value in vital_data.model_dump().items():
            setattr(vital, field, value)
        session.commit()
        session.refresh(vital)
        return vital


@app.get(
    "/patients/{patient_id}/encounters",
    response_model=list[EncounterRead],
)
def read_patient_encounters(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        query = (
            select(Encounter)
            .where(Encounter.patient_id == patient_id)
            .order_by(Encounter.visit_date.desc(), Encounter.id.desc())
        )
        return list(session.scalars(query).all())


@app.post(
    "/patients/{patient_id}/encounters",
    response_model=EncounterRead,
    status_code=201,
)
def create_patient_encounter(
    patient_id: int,
    encounter_data: EncounterCreate,
):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        encounter = Encounter(
            patient_id=patient_id, **encounter_data.model_dump()
        )
        session.add(encounter)
        session.commit()
        session.refresh(encounter)
        return encounter


@app.put(
    "/encounters/{encounter_id}",
    response_model=EncounterRead,
)
def update_encounter(
    encounter_id: int,
    encounter_data: EncounterCreate,
):
    with Session(engine) as session:
        encounter = session.get(Encounter, encounter_id)
        if encounter is None:
            raise HTTPException(status_code=404, detail="Visit note not found")

        for field, value in encounter_data.model_dump().items():
            setattr(encounter, field, value)

        session.commit()
        session.refresh(encounter)
        return encounter


@app.get(
    "/patients/{patient_id}/appointments",
    response_model=list[AppointmentRead],
)
def read_patient_appointments(patient_id: int):
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        query = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(
                Appointment.scheduled_date.desc(),
                Appointment.start_time.desc(),
                Appointment.id.desc(),
            )
        )
        return list(session.scalars(query).all())


@app.post(
    "/patients/{patient_id}/appointments",
    response_model=AppointmentRead,
    status_code=201,
)
def create_patient_appointment(
    patient_id: int,
    appointment_data: AppointmentCreate,
):
    with Session(engine) as session:
        # Serialize scheduling changes for this patient before checking the slot.
        patient = session.scalar(
            select(Patient).where(Patient.id == patient_id).with_for_update()
        )
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        ensure_appointment_slot_open(session, patient_id, appointment_data)

        appointment = Appointment(
            patient_id=patient_id, **appointment_data.model_dump()
        )
        session.add(appointment)
        session.commit()
        session.refresh(appointment)
        return appointment


@app.put(
    "/appointments/{appointment_id}",
    response_model=AppointmentRead,
)
def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentCreate,
):
    with Session(engine) as session:
        appointment = session.get(Appointment, appointment_id)
        if appointment is None:
            raise HTTPException(status_code=404, detail="Appointment not found")

        # Match the create path's patient lock, including on rescheduling.
        patient_id = session.scalar(
            select(Patient.id)
            .where(Patient.id == appointment.patient_id)
            .with_for_update()
        )
        if patient_id is None:
            raise HTTPException(status_code=404, detail="Patient not found")

        ensure_appointment_slot_open(
            session,
            patient_id,
            appointment_data,
            exclude_appointment_id=appointment_id,
        )

        for field, value in appointment_data.model_dump().items():
            setattr(appointment, field, value)

        session.commit()
        session.refresh(appointment)
        return appointment

