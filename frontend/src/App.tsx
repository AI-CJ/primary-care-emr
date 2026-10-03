import { useState } from 'react'

type Patient = {
  id: number
  first_name: string
  last_name: string
  date_of_birth: string
}

function App() {
  const [search, setSearch] = useState('')
  const [patients, setPatients] = useState<Patient[]>([])

  async function searchPatients() {
    const response = await fetch(
      `http://127.0.0.1:8000/patients?search=${encodeURIComponent(search)}`
    )

    const data = await response.json()
    setPatients(data)
  }

  return (
    <main>
      <h1>Patient Search</h1>

      <form
        onSubmit={(event) => {
          event.preventDefault()
          searchPatients()
        }}
      >
        <input
          type="text"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search patients"
        />

        <button type="submit">
          Search
        </button>
      </form>

      <ul>
        {patients.map((patient) => (
          <li key={patient.id}>
            {patient.last_name}, {patient.first_name} — {patient.date_of_birth}
          </li>
        ))}
      </ul>
    </main>
  )
}

export default App