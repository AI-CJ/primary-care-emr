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
