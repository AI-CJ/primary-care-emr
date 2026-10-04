import { useState } from 'react'

import './App.css'

import {
  API_BASE_URL,
  getApiErrorMessage,
} from './api'

import PatientForm from './components/PatientForm'

import type { Patient } from './types'


const sexAtBirthLabels: Record<
  Patient['sex_at_birth'],
  string
> = {
  female: 'Female',
  male: 'Male',
  intersex:
    'Intersex / another sex variation',
  unknown: 'Unknown',
  prefer_not_to_answer:
    'Prefer not to answer',
}


function patientPronouns(
  patient: Patient,
): string {
  if (!patient.pronouns) {
    return 'Pronouns not recorded'
  }

  if (patient.pronouns === 'other') {
    return (
      patient.custom_pronouns ??
      'Other pronouns'
    )
  }

  if (
    patient.pronouns ===
    'prefer_not_to_answer'
  ) {
    return 'Prefer not to answer'
  }

  return patient.pronouns
}


function App() {
  const [search, setSearch] =
    useState('')

  const [patients, setPatients] =
    useState<Patient[]>([])

  const [
    selectedPatient,
    setSelectedPatient,
  ] = useState<Patient | null>(null)

  const [
    isAddingPatient,
    setIsAddingPatient,
  ] = useState(false)

  const [
    isEditingPatient,
    setIsEditingPatient,
  ] = useState(false)

  const [error, setError] =
    useState<string | null>(null)

  const [isSearching, setIsSearching] =
    useState(false)

  const [hasSearched, setHasSearched] =
    useState(false)


  async function searchPatients() {
    setError(null)
    setIsSearching(true)
    setHasSearched(true)

    try {
      const response = await fetch(
        `${API_BASE_URL}/patients?search=${encodeURIComponent(
          search
        )}`
      )

      if (!response.ok) {
        setError(
          await getApiErrorMessage(response)
        )

        return
      }

      const data: Patient[] =
        await response.json()

      setPatients(data)
    } catch (requestError) {
      console.error(requestError)

      setError(
        'The server could not be reached. Try again.'
      )
    } finally {
      setIsSearching(false)
    }
  }


  async function openPatient(
    patientId: number,
  ) {
    setError(null)

    try {
      const response = await fetch(
        `${API_BASE_URL}/patients/${patientId}`
      )

      if (!response.ok) {
        setError(
          await getApiErrorMessage(response)
        )

        return
      }

      const patient: Patient =
        await response.json()

      setSelectedPatient(patient)
    } catch (requestError) {
      console.error(requestError)

      setError(
        'The patient record could not be opened.'
      )
    }
  }


  if (isAddingPatient) {
    return (
      <main className="chart-page">
        <section className="patient-chart">
          <button
            className="back-button"
            type="button"
            onClick={() =>
              setIsAddingPatient(false)
            }
          >
            ← Back to patient search
          </button>


          <header className="patient-header">
            <div>
              <p className="eyebrow">
                Patient Registry
              </p>

              <h1>Add Patient</h1>

              <p className="patient-meta">
                Create a new synthetic patient
                record.
              </p>
            </div>
          </header>


          <PatientForm
            onPatientSaved={(patientId) => {
              setIsAddingPatient(false)

              void openPatient(patientId)
            }}
          />
        </section>
      </main>
    )
  }


  if (
    isEditingPatient &&
    selectedPatient
  ) {
    return (
      <main className="chart-page">
        <section className="patient-chart">
          <button
            className="back-button"
            type="button"
            onClick={() =>
              setIsEditingPatient(false)
            }
          >
            ← Back to patient overview
          </button>


          <header className="patient-header">
            <div>
              <p className="eyebrow">
                Patient Registry
              </p>

              <h1>Edit Patient</h1>

              <p className="patient-meta">
                Update demographic information.
              </p>
            </div>
          </header>


          <PatientForm
            patient={selectedPatient}
            onPatientSaved={(patientId) => {
              setIsEditingPatient(false)

              void openPatient(patientId)
            }}
          />
        </section>
      </main>
    )
  }


  if (selectedPatient) {
    return (
      <main className="chart-page">
        <section className="patient-chart">
          <button
            className="back-button"
            type="button"
            onClick={() =>
              setSelectedPatient(null)
            }
          >
            ← Back to patient search
          </button>


          <header className="patient-header">
            <div>
              <p className="eyebrow">
                Patient Overview
              </p>


              <h1>
                {selectedPatient.first_name}{' '}

                {selectedPatient.preferred_name &&
                  `(${selectedPatient.preferred_name}) `}

                {selectedPatient.middle_name &&
                  `${selectedPatient.middle_name} `}

                {selectedPatient.last_name}

                {selectedPatient.suffix &&
                  ` ${selectedPatient.suffix}`}
              </h1>


              <p className="patient-meta">
                DOB{' '}
                {selectedPatient.date_of_birth}

                {' · '}

                {patientPronouns(
                  selectedPatient
                )}

                {' · '}

                {
                  sexAtBirthLabels[
                    selectedPatient
                      .sex_at_birth
                  ]
                }
              </p>


              <button
                className="add-patient-button"
                type="button"
                onClick={() =>
                  setIsEditingPatient(true)
                }
              >
                Edit Patient
              </button>
            </div>
          </header>


          <div className="overview-grid">
            <section className="overview-card">
              <h2>Problems</h2>
              <p>No problems recorded yet.</p>
            </section>

            <section className="overview-card">
              <h2>Medications</h2>
              <p>No medications recorded yet.</p>
            </section>

            <section className="overview-card">
              <h2>Allergies</h2>
              <p>No allergies recorded yet.</p>
            </section>

            <section className="overview-card">
              <h2>Vitals</h2>
              <p>No vitals recorded yet.</p>
            </section>
          </div>
        </section>
      </main>
    )
  }


  return (
    <main className="search-page">
      <section className="search-panel">
        <div className="search-panel-header">
          <h1>Patient Search</h1>

          <button
            className="add-patient-button"
            type="button"
            onClick={() =>
              setIsAddingPatient(true)
            }
          >
            + Add Patient
          </button>
        </div>


        <form
          className="search-form"
          onSubmit={(event) => {
            event.preventDefault()

            void searchPatients()
          }}
        >
          <input
            className="search-input"
            type="text"
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
            placeholder="Search patients"
          />

          <button
            className="search-button"
            type="submit"
            disabled={isSearching}
          >
            {isSearching
              ? 'Searching...'
              : 'Search'}
          </button>
        </form>


        {error && (
          <p
            className="form-error"
            role="alert"
          >
            {error}
          </p>
        )}


        {hasSearched &&
          !isSearching &&
          !error &&
          patients.length === 0 && (
            <p className="empty-message">
              No patients found.
            </p>
          )}


        <ul className="patient-list">
          {patients.map((patient) => (
            <li key={patient.id}>
              <button
                className="patient-result"
                type="button"
                onClick={() => {
                  void openPatient(
                    patient.id
                  )
                }}
              >
                <span className="patient-name">
                  {patient.last_name},{' '}
                  {patient.first_name}

                  {patient.preferred_name &&
                    ` (${patient.preferred_name})`}
                </span>

                <span className="patient-dob">
                  DOB {patient.date_of_birth}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}


export default App