export type SexAtBirth =
  | 'female'
  | 'male'
  | 'intersex'
  | 'unknown'
  | 'prefer_not_to_answer'

export type Pronouns =
  | 'he/him'
  | 'she/her'
  | 'they/them'
  | 'other'
  | 'prefer_not_to_answer'
  | null

export type Patient = {
  id: number
  first_name: string
  preferred_name: string | null
  middle_name: string | null
  last_name: string
  suffix: string | null
  date_of_birth: string
  pronouns: Pronouns
  custom_pronouns: string | null
  sex_at_birth: SexAtBirth
}

export type PatientInput = Omit<Patient, 'id'>

export type ProblemStatus =
  | 'active'
  | 'resolved'

export type Problem = {
  id: number
  patient_id: number
  name: string
  status: ProblemStatus
  onset_date: string | null
  resolved_date: string | null
  notes: string | null
}

export type ProblemInput = Omit<Problem, 'id' | 'patient_id'>

export type MedicationStatus =
  | 'active'
  | 'completed'
  | 'discontinued'

export type Medication = {
  id: number
  patient_id: number
  name: string
  strength: string | null
  dose: string | null
  route: string | null
  frequency: string | null
  status: MedicationStatus
  start_date: string | null
  end_date: string | null
  instructions: string | null
}

export type MedicationInput = Omit<Medication, 'id' | 'patient_id'>

export type AllergySeverity =
  | 'mild'
  | 'moderate'
  | 'severe'
  | 'unknown'

export type AllergyStatus =
  | 'active'
  | 'inactive'

export type Allergy = {
  id: number
  patient_id: number
  allergen: string
  reaction: string | null
  severity: AllergySeverity
  status: AllergyStatus
  onset_date: string | null
  notes: string | null
}

export type AllergyInput = Omit<Allergy, 'id' | 'patient_id'>

export type Vital = {
  id: number
  patient_id: number
  recorded_on: string
  systolic_bp: number | null
  diastolic_bp: number | null
  heart_rate: number | null
  respiratory_rate: number | null
  temperature_c: number | null
  oxygen_saturation: number | null
  height_cm: number | null
  weight_kg: number | null
  notes: string | null
}

export type VitalInput = Omit<Vital, 'id' | 'patient_id'>

export type Encounter = {
  id: number
  patient_id: number
  appointment_id: number | null
  visit_date: string
  reason_for_visit: string
  subjective: string | null
  objective: string | null
  assessment: string | null
  plan: string | null
  finalized_at: string | null
}

export type EncounterProblem = {
  id: number
  encounter_id: number
  problem_id: number
  problem_name_at_link: string
  problem_status_at_link: ProblemStatus
  linked_at: string
}

export type EncounterMedication = {
  id: number
  encounter_id: number
  medication_id: number
  name_at_link: string
  strength_at_link: string | null
  dose_at_link: string | null
  route_at_link: string | null
  frequency_at_link: string | null
  status_at_link: MedicationStatus
  start_date_at_link: string | null
  end_date_at_link: string | null
  instructions_at_link: string | null
  linked_at: string
}

export type EncounterAllergy = {
  id: number
  encounter_id: number
  allergy_id: number
  allergen_at_link: string
  reaction_at_link: string | null
  severity_at_link: AllergySeverity
  status_at_link: AllergyStatus
  onset_date_at_link: string | null
  notes_at_link: string | null
  linked_at: string
}

export type EncounterVital = {
  id: number
  encounter_id: number
  vital_id: number
  recorded_on_at_link: string
  systolic_bp_at_link: number | null
  diastolic_bp_at_link: number | null
  heart_rate_at_link: number | null
  respiratory_rate_at_link: number | null
  temperature_c_at_link: number | null
  oxygen_saturation_at_link: number | null
  height_cm_at_link: number | null
  weight_kg_at_link: number | null
  notes_at_link: string | null
  linked_at: string
}

export type LabOrderPriority = 'routine' | 'urgent'

export type LabOrder = {
  id: number
  encounter_id: number
  test_name: string
  priority: LabOrderPriority
  clinical_reason: string | null
  status: 'ordered' | 'resulted' | 'cancelled'
  ordered_at: string
  cancelled_at: string | null
  cancellation_reason: string | null
}

export type LabOrderInput = Pick<LabOrder, 'test_name' | 'priority' | 'clinical_reason'>

export type LabResult = {
  id: number
  lab_order_id: number
  collected_on: string
  result_text: string
  reported_at: string
}

export type EncounterAddendum = {
  id: number
  encounter_id: number
  content: string
  created_at: string
}

export type EncounterInput = Omit<
  Encounter,
  'id' | 'patient_id' | 'appointment_id' | 'finalized_at'
> & { appointment_id?: number | null }

export type AppointmentStatus =
  | 'scheduled'
  | 'checked_in'
  | 'completed'
  | 'cancelled'
  | 'no_show'

export type Appointment = {
  id: number
  patient_id: number
  scheduled_date: string
  start_time: string
  duration_minutes: number
  reason_for_visit: string
  status: AppointmentStatus
}

export type AppointmentInput = Omit<Appointment, 'id' | 'patient_id'>

export type AppointmentStatusChange = {
  id: number
  appointment_id: number
  previous_status: AppointmentStatus | null
  new_status: AppointmentStatus
  changed_at: string
}


export type SchedulePatient = Pick<
  Patient,
  'id' | 'first_name' | 'preferred_name' | 'last_name' | 'date_of_birth'
>

export type ScheduleEntry = {
  appointment: Appointment
  patient: SchedulePatient
}
