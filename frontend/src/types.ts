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
