import { useState } from 'react'
import './App.css'

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

function App() {
  const [search, setSearch] = useState('')
  const [patients, setPatients] = useState<Patient[]>([])
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null)

  async function searchPatients() {
    const response = await fetch(
      `http://127.0.0.1:8000/patients?search=${encodeURIComponent(search)}`
    )

    const data = await response.json()
    setPatients(data)
  }

  async function openPatient(patientId: number) {
    const response = await fetch(
      `http://127.0.0.1:8000/patients/${patientId}`
  )

    const patient = await response.json()
    setSelectedPatient(patient)
  }

  if (selectedPatient) {
    return (
      <main className="chart-page">
        <section className="patient-chart">
          <button
            className="back-button"
            type="button"
            onClick={() => setSelectedPatient(null)}
          >
            ← Back to patient search
          </button>

          <header className="patient-header">
            <div>
              <p className="eyebrow">Patient Overview</p>

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
                DOB {selectedPatient.date_of_birth}
                {' · '}
                {selectedPatient.pronouns ?? 'Pronouns not recorded'}
                {' · '}
                {selectedPatient.sex_at_birth ??
                  'Sex at birth not recorded'}
              </p>
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
        <h1>Patient Search</h1>

        <form
          className="search-form"
          onSubmit={(event) => {
            event.preventDefault()
            searchPatients()
          }}
        >
          <input
            className="search-input"
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search patients"
          />

          <button className="search-button" type="submit">
            Search
          </button>
        </form>

        <ul className="patient-list">
          {patients.map((patient) => (
            <li key={patient.id}>
              <button
                className="patient-result"
                type="button"
                onClick={() => openPatient(patient.id)}
              >
                <span className="patient-name">
                  {patient.last_name}, {patient.first_name}
                  {patient.preferred_name && ` (${patient.preferred_name})`}
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