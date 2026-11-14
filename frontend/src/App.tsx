import { useState } from 'react'

import './App.css'

import {
  API_BASE_URL,
  getApiErrorMessage,
} from './api'

import ActiveCareGoalsWorklist from './components/ActiveCareGoalsWorklist'
import AllergyList from './components/AllergyList'
import AppointmentList from './components/AppointmentList'
import CareGoals from './components/CareGoals'
import ClinicSchedule, { localDate } from './components/ClinicSchedule'
import PastAppointmentsWorklist from './components/PastAppointmentsWorklist'
import EncounterList from './components/EncounterList'
import FollowUpTasks from './components/FollowUpTasks'
import OpenFollowUpTasksWorklist from './components/OpenFollowUpTasksWorklist'
import MedicationList from './components/MedicationList'
import PatientTimeline from './components/PatientTimeline'
import PatientPortalPreview from './components/PatientPortalPreview'
import PatientLabHistory from './components/PatientLabHistory'
import PendingLabWorklist from './components/PendingLabWorklist'
import UnreleasedLabResultsWorklist from './components/UnreleasedLabResultsWorklist'
import PendingReferralWorklist from './components/PendingReferralWorklist'
import PatientReferralHistory from './components/PatientReferralHistory'
import PatientForm from './components/PatientForm'
import ProblemList from './components/ProblemList'
import VitalList from './components/VitalList'

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

  const [showSchedule, setShowSchedule] =
    useState(false)

  const [showPastAppointments, setShowPastAppointments] =
    useState(false)

  const [showPortalPreview, setShowPortalPreview] =
    useState(false)

  const [showPendingLabs, setShowPendingLabs] =
    useState(false)

  const [showUnreleasedLabResults, setShowUnreleasedLabResults] =
    useState(false)

  const [showPendingReferrals, setShowPendingReferrals] =
    useState(false)

  const [showActiveCareGoals, setShowActiveCareGoals] =
    useState(false)

  const [showOpenFollowUpTasks, setShowOpenFollowUpTasks] =
    useState(false)

  const [scheduleDay, setScheduleDay] =
    useState(localDate)

  const [patients, setPatients] =
    useState<Patient[]>([])

  const [
    selectedPatient,
    setSelectedPatient,
  ] = useState<Patient | null>(null)

  const [appointmentToReview, setAppointmentToReview] =
    useState<number | null>(null)

  const [noteToReview, setNoteToReview] = useState<{
    id: number
    request: number
  } | null>(null)

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
    appointmentId: number | null = null,
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
      setAppointmentToReview(appointmentId)
      setNoteToReview(null)
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


  if (selectedPatient && showPortalPreview) {
    return (
      <PatientPortalPreview
        patient={selectedPatient}
        onBack={() => setShowPortalPreview(false)}
      />
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
            ← Back to {showOpenFollowUpTasks ? 'open follow-ups' : showActiveCareGoals ? 'active care goals' : showPendingReferrals ? 'pending referrals' : showUnreleasedLabResults ? 'results to release' : showPendingLabs ? 'pending labs' : showPastAppointments ? 'past appointments' : showSchedule ? 'clinic schedule' : 'patient search'}
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
              <button
                className="secondary-action-button"
                type="button"
                onClick={() => setShowPortalPreview(true)}
              >
                Preview Patient Portal
              </button>
            </div>
          </header>


          <div className="overview-grid">
            <PatientTimeline key={selectedPatient.id} patientId={selectedPatient.id} />

            <ProblemList patientId={selectedPatient.id} />

            <MedicationList patientId={selectedPatient.id} />

            <AllergyList patientId={selectedPatient.id} />

            <VitalList patientId={selectedPatient.id} />

            <CareGoals key={selectedPatient.id} patientId={selectedPatient.id} />

            <FollowUpTasks key={selectedPatient.id} patientId={selectedPatient.id} />

            <PatientLabHistory
              key={selectedPatient.id}
              patientId={selectedPatient.id}
            />

            <PatientReferralHistory
              key={selectedPatient.id}
              patientId={selectedPatient.id}
            />

            <EncounterList
              patientId={selectedPatient.id}
              noteToReview={noteToReview}
            />

            <AppointmentList
              key={selectedPatient.id}
              patientId={selectedPatient.id}
              highlightAppointmentId={appointmentToReview}
              onOpenVisitNote={(id) => setNoteToReview((current) => ({
                id,
                request: (current?.request ?? 0) + 1,
              }))}
            />
          </div>
        </section>
      </main>
    )
  }


  if (showOpenFollowUpTasks) {
    return (
      <OpenFollowUpTasksWorklist
        onBack={() => {
          setError(null)
          setShowOpenFollowUpTasks(false)
        }}
        onOpenPatient={(patientId) => {
          void openPatient(patientId)
        }}
        patientError={error}
      />
    )
  }

  if (showActiveCareGoals) {
    return (
      <ActiveCareGoalsWorklist
        onBack={() => {
          setError(null)
          setShowActiveCareGoals(false)
        }}
        onOpenPatient={(patientId) => {
          void openPatient(patientId)
        }}
        patientError={error}
      />
    )
  }

  if (showPendingReferrals) {
    return (
      <PendingReferralWorklist
        onBack={() => {
          setError(null)
          setShowPendingReferrals(false)
        }}
        onOpenPatient={(patientId) => {
          void openPatient(patientId)
        }}
        patientError={error}
      />
    )
  }

  if (showUnreleasedLabResults) {
    return (
      <UnreleasedLabResultsWorklist
        onBack={() => {
          setError(null)
          setShowUnreleasedLabResults(false)
        }}
        onOpenPatient={(patientId) => {
          void openPatient(patientId)
        }}
        patientError={error}
      />
    )
  }

  if (showPendingLabs) {
    return (
      <PendingLabWorklist
        onBack={() => {
          setError(null)
          setShowPendingLabs(false)
        }}
        onOpenPatient={(patientId) => {
          void openPatient(patientId)
        }}
        patientError={error}
      />
    )
  }


  if (showPastAppointments) {
    return (
      <PastAppointmentsWorklist
        onBack={() => {
          setError(null)
          setShowPastAppointments(false)
        }}
        onOpenPatient={(patientId, appointmentId) => {
          void openPatient(patientId, appointmentId)
        }}
        patientError={error}
      />
    )
  }

  if (showSchedule) {
    return (
      <ClinicSchedule
        day={scheduleDay}
        onDayChange={setScheduleDay}
        onBack={() => {
          setError(null)
          setShowSchedule(false)
        }}
        onOpenPatient={(patientId, appointmentId) => {
          void openPatient(patientId, appointmentId)
        }}
        patientError={error}
      />
    )
  }


  return (
    <main className="search-page">
      <section className="search-panel">
        <div className="search-panel-header">
          <h1>Patient Search</h1>

          <div className="search-header-actions">
            <button
              className="secondary-action-button"
              type="button"
              onClick={() => {
                setError(null)
                setShowPendingLabs(false)
                setShowPendingReferrals(false)
                setShowActiveCareGoals(false)
                setShowOpenFollowUpTasks(false)
                setShowSchedule(true)
              }}
            >
              Clinic Schedule
            </button>
            <button
              className="secondary-action-button"
              type="button"
              onClick={() => {
                setError(null)
                setShowPastAppointments(true)
              }}
            >
              Past Appointments
            </button>
            <button
              className="secondary-action-button"
              type="button"
              onClick={() => {
                setError(null)
                setShowSchedule(false)
                setShowPendingReferrals(false)
                setShowActiveCareGoals(false)
                setShowOpenFollowUpTasks(false)
                setShowPendingLabs(true)
              }}
            >
              Pending Labs
            </button>
            <button
              className="secondary-action-button"
              type="button"
              onClick={() => {
                setError(null)
                setShowSchedule(false)
                setShowPendingLabs(false)
                setShowPendingReferrals(false)
                setShowActiveCareGoals(false)
                setShowOpenFollowUpTasks(false)
                setShowUnreleasedLabResults(true)
              }}
            >
              Results to Release
            </button>
            <button
              className="secondary-action-button"
              type="button"
              onClick={() => {
                setError(null)
                setShowSchedule(false)
                setShowPendingLabs(false)
                setShowActiveCareGoals(false)
                setShowOpenFollowUpTasks(false)
                setShowPendingReferrals(true)
              }}
            >
              Pending Referrals
            </button>
            <button
              className="secondary-action-button"
              type="button"
              onClick={() => {
                setError(null)
                setShowSchedule(false)
                setShowPendingLabs(false)
                setShowPendingReferrals(false)
                setShowOpenFollowUpTasks(false)
                setShowActiveCareGoals(true)
              }}
            >
              Active Care Goals
            </button>
            <button
              className="secondary-action-button"
              type="button"
              onClick={() => {
                setError(null)
                setShowSchedule(false)
                setShowPendingLabs(false)
                setShowPendingReferrals(false)
                setShowActiveCareGoals(false)
                setShowOpenFollowUpTasks(true)
              }}
            >
              Open Follow-ups
            </button>
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
