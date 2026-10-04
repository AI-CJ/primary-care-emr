import {
  useState,
  type FormEvent,
} from 'react'

import {
  API_BASE_URL,
  getApiErrorMessage,
} from '../api'

import type {
  Patient,
  PatientInput,
  Pronouns,
  SexAtBirth,
} from '../types'


type PatientFormProps = {
  patient?: Patient
  onPatientSaved: (patientId: number) => void
}

type PronounSelection =
  Exclude<Pronouns, null> | ''


function PatientForm({
  patient,
  onPatientSaved,
}: PatientFormProps) {
  const [pronouns, setPronouns] =
    useState<PronounSelection>(
      patient?.pronouns ?? ''
    )

  const [isSaving, setIsSaving] =
    useState(false)

  const [error, setError] =
    useState<string | null>(null)


  function optionalText(
    formData: FormData,
    name: string,
  ): string | null {
    const value = String(
      formData.get(name) ?? ''
    ).trim()

    return value || null
  }


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setError(null)
    setIsSaving(true)

    const formData =
      new FormData(event.currentTarget)

    const selectedPronouns =
      optionalText(
        formData,
        'pronouns',
      ) as Pronouns

    const patientData: PatientInput = {
      first_name: String(
        formData.get('first_name') ?? ''
      ).trim(),

      preferred_name: optionalText(
        formData,
        'preferred_name',
      ),

      middle_name: optionalText(
        formData,
        'middle_name',
      ),

      last_name: String(
        formData.get('last_name') ?? ''
      ).trim(),

      suffix: optionalText(
        formData,
        'suffix',
      ),

      date_of_birth: String(
        formData.get('date_of_birth') ?? ''
      ),

      sex_at_birth: String(
        formData.get('sex_at_birth') ?? ''
      ) as SexAtBirth,

      pronouns: selectedPronouns,

      custom_pronouns:
        selectedPronouns === 'other'
          ? optionalText(
              formData,
              'custom_pronouns',
            )
          : null,
    }

    const url = patient
      ? `${API_BASE_URL}/patients/${patient.id}`
      : `${API_BASE_URL}/patients`

    try {
      const response = await fetch(url, {
        method: patient ? 'PUT' : 'POST',

        headers: {
          'Content-Type': 'application/json',
        },

        body: JSON.stringify(
          patientData
        ),
      })

      if (!response.ok) {
        setError(
          await getApiErrorMessage(response)
        )

        return
      }

      const savedPatient: Patient =
        await response.json()

      onPatientSaved(savedPatient.id)
    } catch (requestError) {
      console.error(requestError)

      setError(
        'The server could not be reached. Try again.'
      )
    } finally {
      setIsSaving(false)
    }
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
            maxLength={100}
            defaultValue={
              patient?.first_name ?? ''
            }
          />
        </label>


        <label className="form-field">
          <span>Preferred name</span>

          <input
            name="preferred_name"
            type="text"
            maxLength={100}
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
            maxLength={100}
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
            maxLength={100}
            defaultValue={
              patient?.last_name ?? ''
            }
          />
        </label>


        <label className="form-field">
          <span>Suffix</span>

          <input
            name="suffix"
            type="text"
            maxLength={20}
            placeholder="Jr., Sr., III..."
            defaultValue={
              patient?.suffix ?? ''
            }
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
          <span>
            Sex assigned at birth *
          </span>

          <select
            name="sex_at_birth"
            required
            defaultValue={
              patient?.sex_at_birth ?? ''
            }
          >
            <option
              value=""
              disabled
            >
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
              setPronouns(
                event.target
                  .value as PronounSelection
              )
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
            <span>
              Custom pronouns *
            </span>

            <input
              name="custom_pronouns"
              type="text"
              required
              maxLength={100}
              defaultValue={
                patient?.custom_pronouns ??
                ''
              }
            />
          </label>
        )}
      </div>


      {error && (
        <p
          className="form-error"
          role="alert"
        >
          {error}
        </p>
      )}


      <button
        className="save-patient-button"
        type="submit"
        disabled={isSaving}
      >
        {isSaving
          ? 'Saving...'
          : patient
            ? 'Save Changes'
            : 'Save Patient'}
      </button>
    </form>
  )
}


export default PatientForm