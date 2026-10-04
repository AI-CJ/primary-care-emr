import { useState, type FormEvent } from 'react'

type Patient = {
  id: number
  first_name: string
  preferred_name: string | null
  middle_name: string | null
  last_name: string
  suffix: string | null
  date_of_birth: string
  pronouns: string | null
  custom_pronouns: string | null
  sex_at_birth: string
}

type PatientFormProps = {
  patient?: Patient
  onPatientSaved: (patientId: number) => void
}

function PatientForm({
  patient,
  onPatientSaved,
}: PatientFormProps) {
  const [pronouns, setPronouns] = useState(
    patient?.pronouns ?? ''
  )

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault()

    const formData = new FormData(event.currentTarget)

    const patientData = {
      first_name: formData.get('first_name'),
      preferred_name:
        formData.get('preferred_name') || null,
      middle_name:
        formData.get('middle_name') || null,
      last_name: formData.get('last_name'),
      suffix: formData.get('suffix') || null,
      date_of_birth: formData.get('date_of_birth'),
      sex_at_birth: formData.get('sex_at_birth'),
      pronouns: formData.get('pronouns') || null,
      custom_pronouns:
        pronouns === 'other'
          ? formData.get('custom_pronouns') || null
          : null,
    }

    const url = patient
      ? `http://127.0.0.1:8000/patients/${patient.id}`
      : 'http://127.0.0.1:8000/patients'

    const response = await fetch(url, {
      method: patient ? 'PUT' : 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(patientData),
    })

    if (!response.ok) {
      return
    }

    const savedPatient = await response.json()

    onPatientSaved(savedPatient.id)
  }

  return (
    <form
      className="patient-form"
      onSubmit={handleSubmit}
    >
      <div className="form-grid">
        <label className="form-field">
          <span>First name *</span>

          <input
            name="first_name"
            type="text"
            required
            defaultValue={patient?.first_name ?? ''}
          />
        </label>

        <label className="form-field">
          <span>Preferred name</span>

          <input
            name="preferred_name"
            type="text"
            defaultValue={
              patient?.preferred_name ?? ''
            }
          />
        </label>

        <label className="form-field">
          <span>Middle name</span>

          <input
            name="middle_name"
            type="text"
            defaultValue={
              patient?.middle_name ?? ''
            }
          />
        </label>

        <label className="form-field">
          <span>Last name *</span>

          <input
            name="last_name"
            type="text"
            required
            defaultValue={patient?.last_name ?? ''}
          />
        </label>

        <label className="form-field">
          <span>Suffix</span>

          <input
            name="suffix"
            type="text"
            placeholder="Jr., Sr., III..."
            defaultValue={patient?.suffix ?? ''}
          />
        </label>

        <label className="form-field">
          <span>Date of birth *</span>

          <input
            name="date_of_birth"
            type="date"
            required
            defaultValue={
              patient?.date_of_birth ?? ''
            }
          />
        </label>

        <label className="form-field">
          <span>Sex assigned at birth *</span>

          <select
            name="sex_at_birth"
            required
            defaultValue={
              patient?.sex_at_birth ?? ''
            }
          >
            <option value="" disabled>
              Select an option
            </option>

            <option value="female">
              Female
            </option>

            <option value="male">
              Male
            </option>

            <option value="intersex">
              Intersex / another sex variation
            </option>

            <option value="unknown">
              Unknown
            </option>

            <option value="prefer_not_to_answer">
              Prefer not to answer
            </option>
          </select>
        </label>

        <label className="form-field">
          <span>Pronouns</span>

          <select
            name="pronouns"
            value={pronouns}
            onChange={(event) =>
              setPronouns(event.target.value)
            }
          >
            <option value="">
              Not recorded
            </option>

            <option value="he/him">
              He / him
            </option>

            <option value="she/her">
              She / her
            </option>

            <option value="they/them">
              They / them
            </option>

            <option value="other">
              Other
            </option>

            <option value="prefer_not_to_answer">
              Prefer not to answer
            </option>
          </select>
        </label>

        {pronouns === 'other' && (
          <label className="form-field">
            <span>Custom pronouns</span>

            <input
              name="custom_pronouns"
              type="text"
              defaultValue={
                patient?.custom_pronouns ?? ''
              }
            />
          </label>
        )}
      </div>

      <button
        className="save-patient-button"
        type="submit"
      >
        {patient ? 'Save Changes' : 'Save Patient'}
      </button>
    </form>
  )
}

export default PatientForm