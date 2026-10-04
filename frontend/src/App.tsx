import { useState } from 'react'
import './App.css'

type Patient = {
  id: number
  first_name: string
  middle_name: string | null
  last_name: string
  suffix: string | null
  date_of_birth: string
  pronouns: string | null
  sex_at_birth: string | null
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
                onClick={() => setSelectedPatient(patient)}
              >
                <span className="patient-name">
                  {patient.last_name}, {patient.first_name}
                </span>

                <span className="patient-dob">
                  DOB {patient.date_of_birth}
                </span>
              </button>
            </li>
          ))}
        </ul>
        {selectedPatient && (
          <section className="patient-detail">
            <h2>
              {selectedPatient.first_name}{' '}
              {selectedPatient.middle_name && `${selectedPatient.middle_name} `}
              {selectedPatient.last_name}
              {selectedPatient.suffix && ` ${selectedPatient.suffix}`}
            </h2>

            <p>
              <strong>Date of birth:</strong> {selectedPatient.date_of_birth}
            </p>

            <p>
              <strong>Pronouns:</strong>{' '}
              {selectedPatient.pronouns ?? 'Not recorded'}
            </p>

            <p>
              <strong>Sex at birth:</strong>{' '}
              {selectedPatient.sex_at_birth ?? 'Not recorded'}
            </p>
          </section>
        )}
      </section>
    </main>
  )
}

export default App