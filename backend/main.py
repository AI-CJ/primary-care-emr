from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.database import engine
from backend.encounters import (
    apply_encounter_update,
    create_encounter,
    create_encounter_addendum,
    finalize_encounter,
)
from backend.encounter_problems import (
    link_encounter_problem,
    list_encounter_problems,
    unlink_encounter_problem,
)
from backend.encounter_medications import (
    link_encounter_medication,
    list_encounter_medications,
    unlink_encounter_medication,
)
from backend.encounter_allergies import (
    link_encounter_allergy,
    list_encounter_allergies,
    unlink_encounter_allergy,
)
from backend.encounter_vitals import (
    link_encounter_vital,
    list_encounter_vitals,
    unlink_encounter_vital,
)
from backend.lab_orders import (
    cancel_lab_order,
    create_lab_order,
    list_lab_orders,
    read_lab_result,
    record_lab_result,
)
from backend.referrals import (
    cancel_referral,
    complete_referral,
    create_referral,
    list_referrals,
    list_patient_referrals,
)
from backend.scheduling import (
    cancel_appointment,
    check_in_appointment,
    complete_appointment,
    ensure_appointment_slot_open,
    list_daily_schedule,
    mark_appointment_no_show,
    record_appointment_status_change,
    reschedule_appointment,
)
from backend.models import (
    Allergy, Appointment, AppointmentStatusChange, Encounter,
    EncounterAddendum, Medication, Patient, Problem, Vital,
)
from backend.schemas import (
    AllergyCreate,
    EncounterAllergyLinkCreate,
    EncounterAllergyRead,
    AllergyRead,
    AppointmentCreate,
    AppointmentRead,
    AppointmentStatusChangeRead,
    EncounterAddendumCreate,
    EncounterAddendumRead,
    EncounterMedicationLinkCreate,
    EncounterMedicationRead,
    EncounterProblemLinkCreate,
    EncounterProblemRead,
    EncounterVitalLinkCreate,
    EncounterVitalRead,
    EncounterCreate,
    EncounterRead,
    EncounterUpdate,
    LabOrderCancel,
    LabOrderCreate,
    LabOrderRead,
    LabResultCreate,
    LabResultRead,
    ReferralCancel,
    ReferralComplete,
    ReferralCreate,
    ReferralRead,
    PatientReferralRead,
    MedicationCreate,
    MedicationRead,
    PatientCreate,
    PatientRead,
    ProblemCreate,
    ProblemRead,
    ScheduleEntryRead,
    SchedulePatientRead,
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
        encounter = create_encounter(session, patient_id, encounter_data)
        session.commit()
        session.refresh(encounter)
        return encounter


@app.put(
    "/encounters/{encounter_id}",
    response_model=EncounterRead,
)
def update_encounter(
    encounter_id: int,
    encounter_data: EncounterUpdate,
):
    with Session(engine) as session:
        encounter = apply_encounter_update(session, encounter_id, encounter_data)
        session.commit()
        session.refresh(encounter)
        return encounter


@app.post(
    "/encounters/{encounter_id}/finalize",
    response_model=EncounterRead,
)
def finalize_patient_encounter(encounter_id: int):
    with Session(engine) as session:
        encounter = finalize_encounter(session, encounter_id)
        session.commit()
        session.refresh(encounter)
        return encounter


@app.get(
    "/encounters/{encounter_id}/addenda",
    response_model=list[EncounterAddendumRead],
)
def read_encounter_addenda(encounter_id: int):
    with Session(engine) as session:
        if session.get(Encounter, encounter_id) is None:
            raise HTTPException(status_code=404, detail="Visit note not found")

        query = (
            select(EncounterAddendum)
            .where(EncounterAddendum.encounter_id == encounter_id)
            .order_by(EncounterAddendum.created_at, EncounterAddendum.id)
        )
        return list(session.scalars(query).all())


@app.post(
    "/encounters/{encounter_id}/addenda",
    response_model=EncounterAddendumRead,
    status_code=201,
)
def add_encounter_addendum(
    encounter_id: int, addendum_data: EncounterAddendumCreate
):
    with Session(engine) as session:
        addendum = create_encounter_addendum(
            session, encounter_id, addendum_data
        )
        session.commit()
        session.refresh(addendum)
        return addendum


@app.get(
    "/encounters/{encounter_id}/problems",
    response_model=list[EncounterProblemRead],
)
def read_encounter_problems(encounter_id: int):
    with Session(engine) as session:
        return list_encounter_problems(session, encounter_id)


@app.post(
    "/encounters/{encounter_id}/problems",
    response_model=EncounterProblemRead,
    status_code=201,
)
def add_encounter_problem(
    encounter_id: int, link_data: EncounterProblemLinkCreate
):
    with Session(engine) as session:
        link = link_encounter_problem(session, encounter_id, link_data)
        session.commit()
        session.refresh(link)
        return link


@app.delete("/encounters/{encounter_id}/problems/{problem_id}", status_code=204)
def remove_encounter_problem(encounter_id: int, problem_id: int):
    with Session(engine) as session:
        unlink_encounter_problem(session, encounter_id, problem_id)
        session.commit()


@app.get(
    "/encounters/{encounter_id}/vitals",
    response_model=list[EncounterVitalRead],
)
def read_encounter_vitals(encounter_id: int):
    with Session(engine) as session:
        return list_encounter_vitals(session, encounter_id)


@app.post(
    "/encounters/{encounter_id}/vitals",
    response_model=EncounterVitalRead,
    status_code=201,
)
def add_encounter_vital(
    encounter_id: int, link_data: EncounterVitalLinkCreate
):
    with Session(engine) as session:
        link = link_encounter_vital(session, encounter_id, link_data)
        session.commit()
        session.refresh(link)
        return link


@app.delete("/encounters/{encounter_id}/vitals/{vital_id}", status_code=204)
def remove_encounter_vital(encounter_id: int, vital_id: int):
    with Session(engine) as session:
        unlink_encounter_vital(session, encounter_id, vital_id)
        session.commit()



@app.get(
    "/encounters/{encounter_id}/medications",
    response_model=list[EncounterMedicationRead],
)
def read_encounter_medications(encounter_id: int):
    with Session(engine) as session:
        return list_encounter_medications(session, encounter_id)


@app.post(
    "/encounters/{encounter_id}/medications",
    response_model=EncounterMedicationRead,
    status_code=201,
)
def add_encounter_medication(
    encounter_id: int, link_data: EncounterMedicationLinkCreate
):
    with Session(engine) as session:
        link = link_encounter_medication(session, encounter_id, link_data)
        session.commit()
        session.refresh(link)
        return link


@app.delete("/encounters/{encounter_id}/medications/{medication_id}", status_code=204)
def remove_encounter_medication(encounter_id: int, medication_id: int):
    with Session(engine) as session:
        unlink_encounter_medication(session, encounter_id, medication_id)
        session.commit()


@app.get(
    "/encounters/{encounter_id}/allergies",
    response_model=list[EncounterAllergyRead],
)
def read_encounter_allergies(encounter_id: int):
    with Session(engine) as session:
        return list_encounter_allergies(session, encounter_id)


@app.post(
    "/encounters/{encounter_id}/allergies",
    response_model=EncounterAllergyRead,
    status_code=201,
)
def add_encounter_allergy(encounter_id: int, link_data: EncounterAllergyLinkCreate):
    with Session(engine) as session:
        link = link_encounter_allergy(session, encounter_id, link_data)
        session.commit()
        session.refresh(link)
        return link


@app.delete("/encounters/{encounter_id}/allergies/{allergy_id}", status_code=204)
def remove_encounter_allergy(encounter_id: int, allergy_id: int):
    with Session(engine) as session:
        unlink_encounter_allergy(session, encounter_id, allergy_id)
        session.commit()


@app.get(
    "/encounters/{encounter_id}/lab-orders",
    response_model=list[LabOrderRead],
)
def read_encounter_lab_orders(encounter_id: int):
    with Session(engine) as session:
        return list_lab_orders(session, encounter_id)


@app.post(
    "/encounters/{encounter_id}/lab-orders",
    response_model=LabOrderRead,
    status_code=201,
)
def add_encounter_lab_order(encounter_id: int, order_data: LabOrderCreate):
    with Session(engine) as session:
        order = create_lab_order(session, encounter_id, order_data)
        session.commit()
        session.refresh(order)
        return order


@app.post(
    "/lab-orders/{order_id}/cancel",
    response_model=LabOrderRead,
)
def cancel_order_request(order_id: int, cancellation: LabOrderCancel):
    with Session(engine) as session:
        order = cancel_lab_order(session, order_id, cancellation)
        session.commit()
        session.refresh(order)
        return order


@app.get(
    "/lab-orders/{order_id}/result",
    response_model=LabResultRead,
)
def read_order_result(order_id: int):
    with Session(engine) as session:
        return read_lab_result(session, order_id)


@app.post(
    "/lab-orders/{order_id}/result",
    response_model=LabResultRead,
    status_code=201,
)
def add_order_result(order_id: int, result_data: LabResultCreate):
    with Session(engine) as session:
        result = record_lab_result(session, order_id, result_data)
        session.commit()
        session.refresh(result)
        return result


@app.get(
    "/patients/{patient_id}/referrals",
    response_model=list[PatientReferralRead],
)
def read_patient_referrals(patient_id: int):
    with Session(engine) as session:
        return [
            PatientReferralRead(
                **ReferralRead.model_validate(referral).model_dump(),
                visit_date=visit_date,
            )
            for referral, visit_date in list_patient_referrals(session, patient_id)
        ]


@app.get(
    "/encounters/{encounter_id}/referrals",
    response_model=list[ReferralRead],
)
def read_encounter_referrals(encounter_id: int):
    with Session(engine) as session:
        return list_referrals(session, encounter_id)


@app.post(
    "/encounters/{encounter_id}/referrals",
    response_model=ReferralRead,
    status_code=201,
)
def add_encounter_referral(encounter_id: int, referral_data: ReferralCreate):
    with Session(engine) as session:
        referral = create_referral(session, encounter_id, referral_data)
        session.commit()
        session.refresh(referral)
        return referral


@app.post(
    "/referrals/{referral_id}/cancel",
    response_model=ReferralRead,
)
def cancel_referral_request(referral_id: int, cancellation: ReferralCancel):
    with Session(engine) as session:
        referral = cancel_referral(session, referral_id, cancellation)
        session.commit()
        session.refresh(referral)
        return referral


@app.post(
    "/referrals/{referral_id}/complete",
    response_model=ReferralRead,
)
def complete_referral_request(referral_id: int, follow_up: ReferralComplete):
    with Session(engine) as session:
        referral = complete_referral(session, referral_id, follow_up)
        session.commit()
        session.refresh(referral)
        return referral


@app.get(
    "/schedule",
    response_model=list[ScheduleEntryRead],
)
def read_daily_schedule(day: date):
    """Read all appointments for a clinic-local day."""
    with Session(engine) as session:
        return [
            ScheduleEntryRead(
                appointment=AppointmentRead.model_validate(appointment),
                patient=SchedulePatientRead.model_validate(patient),
            )
            for appointment, patient in list_daily_schedule(session, day)
        ]


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
        session.flush()
        record_appointment_status_change(session, appointment, None)
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
        appointment = reschedule_appointment(
            session, appointment_id, appointment_data
        )
        session.commit()
        session.refresh(appointment)
        return appointment


@app.post(
    "/appointments/{appointment_id}/check-in",
    response_model=AppointmentRead,
)
def check_in_patient_appointment(appointment_id: int):
    with Session(engine) as session:
        appointment = check_in_appointment(session, appointment_id)
        session.commit()
        session.refresh(appointment)
        return appointment

@app.post(
    "/appointments/{appointment_id}/complete",
    response_model=AppointmentRead,
)
def complete_patient_appointment(appointment_id: int):
    with Session(engine) as session:
        appointment = complete_appointment(session, appointment_id)
        session.commit()
        session.refresh(appointment)
        return appointment


@app.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentRead,
)
def cancel_patient_appointment(appointment_id: int):
    with Session(engine) as session:
        appointment = cancel_appointment(session, appointment_id)
        session.commit()
        session.refresh(appointment)
        return appointment


@app.post(
    "/appointments/{appointment_id}/no-show",
    response_model=AppointmentRead,
)
def mark_patient_appointment_no_show(appointment_id: int):
    with Session(engine) as session:
        appointment = mark_appointment_no_show(session, appointment_id)
        session.commit()
        session.refresh(appointment)
        return appointment


@app.get(
    "/appointments/{appointment_id}/status-history",
    response_model=list[AppointmentStatusChangeRead],
)
def read_appointment_status_history(appointment_id: int):
    with Session(engine) as session:
        appointment = session.get(Appointment, appointment_id)
        if appointment is None:
            raise HTTPException(status_code=404, detail="Appointment not found")

        query = (
            select(AppointmentStatusChange)
            .where(AppointmentStatusChange.appointment_id == appointment_id)
            .order_by(
                AppointmentStatusChange.changed_at,
                AppointmentStatusChange.id,
            )
        )
        return list(session.scalars(query).all())

