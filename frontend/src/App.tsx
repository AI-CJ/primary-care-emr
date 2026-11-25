import { useEffect, useRef, useState } from 'react'

import './App.css'

import {
  API_BASE_URL,
  apiFetch,
  setAccessToken,
  getApiErrorMessage,
} from './api'

import AppointmentChangeRequestsWorklist from './components/AppointmentChangeRequestsWorklist'
import ActiveCareGoalsWorklist from './components/ActiveCareGoalsWorklist'
import AllergyList from './components/AllergyList'
import AppointmentList from './components/AppointmentList'
import CareGoals from './components/CareGoals'
import ClinicSchedule from './components/ClinicSchedule'
import { localDate } from './date'
import PastAppointmentsWorklist from './components/PastAppointmentsWorklist'
import EncounterList from './components/EncounterList'
import FollowUpTasks from './components/FollowUpTasks'
import OpenFollowUpTasksWorklist from './components/OpenFollowUpTasksWorklist'
import MedicationList from './components/MedicationList'
import PatientTimeline from './components/PatientTimeline'
import PatientLifecycleControls from './components/PatientLifecycleControls'
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
import SignIn, { type SignedInAccount } from './components/SignIn'
import PatientPortal from './components/PatientPortal'
import AuditReview from './components/AuditReview'
import WorkspaceNavigation from './components/WorkspaceNavigation'
import StaffDashboard from './components/StaffDashboard'
import { type StaffDestination, staffDestinationLabels } from './workspaceNavigation'
import SectionNavigation, { type SectionOption } from './components/SectionNavigation'
import './ClinicalWorkspace.css'
import { BrandMark } from './components/BrandArtwork'


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


type ChartSection = 'summary' | 'health' | 'appointments' | 'notes' | 'orders' | 'care'
const chartSections: SectionOption<ChartSection>[] = [
  { id: 'summary', label: 'Summary' },
  { id: 'health', label: 'Health record' },
  { id: 'appointments', label: 'Appointments' },
  { id: 'notes', label: 'Visit notes' },
  { id: 'orders', label: 'Labs & referrals' },
  { id: 'care', label: 'Care plan' },
]

function StaffApp({ isAdmin }: { isAdmin: boolean }) {
  const [search, setSearch] =
    useState('')

  const [destination, setDestination] = useState<StaffDestination>('dashboard')
  const [chartSection, setChartSection] = useState<ChartSection>('summary')
  const [showPortalPreview, setShowPortalPreview] = useState(false)
  const dirtyForms = useRef(new WeakSet<HTMLFormElement>())
  const workspaceRef = useRef<HTMLDivElement>(null)
  const openRequest = useRef(0)
  const searchRequest = useRef(0)

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

  const [noteToStart, setNoteToStart] = useState<{
    appointmentId: number
    request: number
  } | null>(null)
  const [notesRefreshCount, setNotesRefreshCount] = useState(0)

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
    useState(true)

  useEffect(() => {
    const controller = new AbortController()
    const request = ++searchRequest.current
    async function loadDirectory() {
      try {
        const response = await apiFetch(API_BASE_URL + '/patients', { signal: controller.signal })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const data: Patient[] = await response.json()
        if (!controller.signal.aborted && request === searchRequest.current) setPatients(data)
      } catch (reason) {
        if (!controller.signal.aborted && request === searchRequest.current) setError(reason instanceof Error ? reason.message : 'Patient directory could not be loaded.')
      } finally {
        if (!controller.signal.aborted && request === searchRequest.current) setIsSearching(false)
      }
    }
    void loadDirectory()
    return () => controller.abort()
  }, [])

  function confirmNavigation() {
    const forms = workspaceRef.current?.querySelectorAll<HTMLFormElement>('form:not(.search-form)')
    if (forms && Array.from(forms).some((form) => dirtyForms.current.has(form) && form.getClientRects().length > 0)) {
      return window.confirm('Leave this screen? Unsaved form changes will be discarded.')
    }
    return true
  }

  function navigate(next: StaffDestination) {
    if (!confirmNavigation()) return
    openRequest.current += 1
    setDestination(next)
    setSelectedPatient(null)
    setIsAddingPatient(false)
    setIsEditingPatient(false)
    setShowPortalPreview(false)
    setNoteToReview(null)
    setNoteToStart(null)
    setAppointmentToReview(null)
    setError(null)
    if (next === 'schedule' && destination === 'dashboard') setScheduleDay(localDate())
    if (next === 'patients') {
      setSearch('')
      void searchPatients('')
    }
    window.scrollTo({ top: 0, behavior: 'auto' })
  }

  function selectChartSection(next: ChartSection) {
    if (next === chartSection || !confirmNavigation()) return
    setChartSection(next)
    setNoteToReview(null)
    setNoteToStart(null)
    setAppointmentToReview(null)
  }

  function returnToDirectory() {
    if (!confirmNavigation()) return
    openRequest.current += 1
    setSelectedPatient(null)
    setShowPortalPreview(false)
    setIsEditingPatient(false)
    if (destination === 'patients') void searchPatients()
  }


  async function searchPatients(query = search) {
    setError(null)
    setIsSearching(true)
    const request = ++searchRequest.current

    try {
      const response = await apiFetch(
        `${API_BASE_URL}/patients?search=${encodeURIComponent(
          query
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

      if (request === searchRequest.current) setPatients(data)
    } catch (requestError) {
      if (request !== searchRequest.current) return
      console.error(requestError)

      setError(
        'The server could not be reached. Try again.'
      )
    } finally {
      if (request === searchRequest.current) setIsSearching(false)
    }
  }


  async function openPatient(
    patientId: number,
    appointmentId: number | null = null,
    noteAction?: 'start' | 'open',
    noteId?: number,
  ) {
    if (!confirmNavigation()) return
    const request = ++openRequest.current
    setError(null)

    try {
      const response = await apiFetch(
        `${API_BASE_URL}/patients/${patientId}`
      )

      if (request !== openRequest.current) return
      if (!response.ok) {
        setError(await getApiErrorMessage(response))
        return
      }

      const patient: Patient =
        await response.json()
      if (request !== openRequest.current) return

      setSelectedPatient(patient)
      setPatients((current) => current.map((item) => item.id === patient.id ? patient : item))
      setChartSection(noteAction ? 'notes'
        : appointmentId !== null ? 'appointments'
        : ['labs', 'results', 'referrals'].includes(destination) ? 'orders'
        : ['goals', 'followups'].includes(destination) ? 'care'
        : 'summary')
      setShowPortalPreview(false)
      setAppointmentToReview(appointmentId)
      setNoteToReview(
        noteAction === 'open' && noteId !== undefined
          ? { id: noteId, request: 1 }
          : null
      )
      setNoteToStart(
        noteAction === 'start' && appointmentId !== null
          ? { appointmentId, request: 1 }
          : null
      )
    } catch (requestError) {
      if (request !== openRequest.current) return
      console.error(requestError)

      setError(
        'The patient record could not be opened.'
      )
    }
  }


  function renderWorkspace() {
    if (isAddingPatient) {
    return (
      <main className="chart-page">
        <section className="patient-chart">
          <button
            className="back-button"
            type="button"
            onClick={() =>
              confirmNavigation() && setIsAddingPatient(false)
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
                Create a new patient record.
              </p>
            </div>
          </header>


          <PatientForm
            onPatientSaved={(patientId) => {
              dirtyForms.current = new WeakSet()
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
              confirmNavigation() && setIsEditingPatient(false)
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
              dirtyForms.current = new WeakSet()
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
            onClick={returnToDirectory}
          >
            ← Back to {destination === 'patients' ? 'patient search' : staffDestinationLabels[destination].toLowerCase()}
          </button>


          <header className="patient-header chart-identity">
            <div>
              <p className="eyebrow">
                Patient chart
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
                Chart #{String(selectedPatient.id).padStart(6, '0')}{' · '}
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


            </div>
            <div className="chart-identity-actions">
              <span className={`chart-state ${selectedPatient.archived_at ? 'chart-state-archived' : ''}`}>
                {selectedPatient.archived_at ? 'Archived' : 'Active'}
              </span>
              <button className="secondary-action-button" type="button"
                disabled={Boolean(selectedPatient.archived_at)}
                onClick={() => confirmNavigation() && setIsEditingPatient(true)}>Edit Patient</button>
              <button className="secondary-action-button" type="button"
                onClick={() => confirmNavigation() && setShowPortalPreview(true)}>Preview Patient Portal</button>
            </div>
          </header>


          <SectionNavigation label="Patient chart sections" options={chartSections}
            current={chartSection} onChange={selectChartSection} />

          <div className="chart-section-heading">
            <h2>{chartSections.find((item) => item.id === chartSection)?.label}</h2>
          </div>
          <div className="overview-grid" key={selectedPatient.id + ':' + chartSection}>
            {chartSection === 'summary' && <>
              <PatientTimeline key={selectedPatient.id} patientId={selectedPatient.id} />
              <PatientLifecycleControls key={selectedPatient.id} patientId={selectedPatient.id}
                onChanged={(patient) => {
                  setSelectedPatient((current) => current?.id === patient.id ? patient : current)
                  setPatients((current) => current.map((item) => item.id === patient.id ? patient : item))
                }} />
            </>}
            {chartSection === 'health' && <>
              <ProblemList patientId={selectedPatient.id} />
              <MedicationList patientId={selectedPatient.id} />
              <AllergyList patientId={selectedPatient.id} />
              <VitalList patientId={selectedPatient.id} />
            </>}
            {chartSection === 'care' && <>
              <CareGoals key={selectedPatient.id} patientId={selectedPatient.id} />
              <FollowUpTasks key={selectedPatient.id} patientId={selectedPatient.id} />
            </>}
            {chartSection === 'orders' && <>
              <PatientLabHistory key={selectedPatient.id} patientId={selectedPatient.id} />
              <PatientReferralHistory key={selectedPatient.id} patientId={selectedPatient.id} />
            </>}
            {chartSection === 'notes' && <EncounterList
              key={selectedPatient.id}
              patientId={selectedPatient.id}
              noteToReview={noteToReview}
              noteToStart={noteToStart}
              onNoteSaved={() => setNotesRefreshCount((count) => count + 1)}
            />}
            {chartSection === 'appointments' && <AppointmentList
              key={selectedPatient.id}
              patientId={selectedPatient.id}
              highlightAppointmentId={appointmentToReview}
              notesRefreshCount={notesRefreshCount}
              onOpenVisitNote={(id) => {
                if (!confirmNavigation()) return
                setNoteToStart(null)
                setNoteToReview((current) => ({ id, request: (current?.request ?? 0) + 1 }))
                setChartSection('notes')
              }}
              onStartVisitNote={(appointmentId) => {
                if (!confirmNavigation()) return
                setNoteToReview(null)
                setNoteToStart((current) => ({ appointmentId, request: (current?.request ?? 0) + 1 }))
                setChartSection('notes')
              }}
            />}
          </div>
        </section>
      </main>
    )
  }


  if (destination === 'dashboard') return <StaffDashboard onNavigate={navigate} />

  if (destination === 'requests') {
    return (
      <AppointmentChangeRequestsWorklist
        onBack={() => { setError(null); setDestination('patients') }}
        onOpenPatient={(patientId, appointmentId) => {
          void openPatient(patientId, appointmentId)
        }}
        patientError={error}
      />
    )
  }

  if (destination === 'followups') {
    return (
      <OpenFollowUpTasksWorklist
        onBack={() => {
          setError(null)
          setDestination('patients')
        }}
        onOpenPatient={(patientId) => {
          void openPatient(patientId)
        }}
        patientError={error}
      />
    )
  }

  if (destination === 'goals') {
    return (
      <ActiveCareGoalsWorklist
        onBack={() => {
          setError(null)
          setDestination('patients')
        }}
        onOpenPatient={(patientId) => {
          void openPatient(patientId)
        }}
        patientError={error}
      />
    )
  }

  if (destination === 'referrals') {
    return (
      <PendingReferralWorklist
        onBack={() => {
          setError(null)
          setDestination('patients')
        }}
        onOpenPatient={(patientId) => {
          void openPatient(patientId)
        }}
        patientError={error}
      />
    )
  }

  if (destination === 'results') {
    return (
      <UnreleasedLabResultsWorklist
        onBack={() => {
          setError(null)
          setDestination('patients')
        }}
        onOpenPatient={(patientId) => {
          void openPatient(patientId)
        }}
        patientError={error}
      />
    )
  }

  if (destination === 'labs') {
    return (
      <PendingLabWorklist
        onBack={() => {
          setError(null)
          setDestination('patients')
        }}
        onOpenPatient={(patientId) => {
          void openPatient(patientId)
        }}
        patientError={error}
      />
    )
  }


  if (destination === 'past') {
    return (
      <PastAppointmentsWorklist
        onBack={() => {
          setError(null)
          setDestination('patients')
        }}
        onOpenPatient={(patientId, appointmentId) => {
          void openPatient(patientId, appointmentId)
        }}
        onStartVisitNote={(patientId, appointmentId) => {
          void openPatient(patientId, appointmentId, 'start')
        }}
        onOpenVisitNote={(patientId, appointmentId, noteId) => {
          void openPatient(patientId, appointmentId, 'open', noteId)
        }}
        patientError={error}
      />
    )
  }

  if (destination === 'schedule') {
    return (
      <ClinicSchedule
        day={scheduleDay}
        onDayChange={setScheduleDay}
        onBack={() => {
          setError(null)
          setDestination('patients')
        }}
        onOpenPatient={(patientId, appointmentId) => {
          void openPatient(patientId, appointmentId)
        }}
        onStartVisitNote={(patientId, appointmentId) => {
          void openPatient(patientId, appointmentId, 'start')
        }}
        onOpenVisitNote={(patientId, appointmentId, noteId) => {
          void openPatient(patientId, appointmentId, 'open', noteId)
        }}
        patientError={error}
      />
    )
  }


  if (destination === 'audit' && isAdmin) return <AuditReview />

  return (
    <main className="search-page directory-page">
      <section className="search-panel directory-panel">
        <div className="search-panel-header">
          <div><p className="workspace-eyebrow">Patient registry</p><h1>Patient Search</h1><p className="workspace-description">Find a patient by name or open their chart from the directory.</p></div>

          <button className="add-patient-button" type="button" onClick={() => setIsAddingPatient(true)}>
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
            type="search"
            aria-label="Search patients"
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


        {!isSearching &&
          !error &&
          patients.length === 0 && (
            <p className="empty-message">
              No patients found.
            </p>
          )}


        {isSearching && <p role="status" className="directory-status">Loading patients…</p>}
        {!isSearching && !error && patients.length > 0 && <div className="directory-list-heading" aria-hidden="true">
          <span>Patient</span><span>Date of birth</span><span>Chart status</span><span></span>
        </div>}
        <ul className="patient-list" aria-label="Patient directory" hidden={isSearching || Boolean(error)}>
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

                <span className="patient-dob">DOB {patient.date_of_birth}</span>
                <span className={`chart-state ${patient.archived_at ? 'chart-state-archived' : ''}`}>{patient.archived_at ? 'Archived' : 'Active'}</span>
                <span className="directory-chevron" aria-hidden="true">›</span>
              </button>
            </li>
          ))}
        </ul>
        {!isSearching && !error && <p className="directory-status" role="status">{patients.length} {patients.length === 1 ? 'patient' : 'patients'} found</p>}
      </section>
    </main>
  )
  }

  return (
    <div className="staff-workspace">
      <WorkspaceNavigation current={selectedPatient || isAddingPatient ? 'patients' : destination}
        isAdmin={isAdmin} onNavigate={navigate} />
      <div className="workspace-content" ref={workspaceRef}
        onChangeCapture={(event) => {
          if (event.target instanceof HTMLElement) {
            const form = event.target.closest('form')
            if (form && !form.classList.contains('search-form')) dirtyForms.current.add(form)
          }
        }}>
        {renderWorkspace()}
      </div>
    </div>
  )
}

function App() {
  const [account, setAccount] = useState<SignedInAccount | null>(null)
  const [signInMode, setSignInMode] = useState<'staff' | 'patient'>('staff')

  useEffect(() => {
    const sessionEnded = () => setAccount(null)
    window.addEventListener('emr:session-ended', sessionEnded)
    return () => window.removeEventListener('emr:session-ended', sessionEnded)
  }, [])

  async function signOut() {
    try {
      await apiFetch(`${API_BASE_URL}/auth/logout`, { method: 'POST' })
    } finally {
      setAccessToken(null)
      setAccount(null)
    }
  }

  if (!account) {
    return (
      <SignIn
        key={signInMode}
        mode={signInMode}
        onModeChange={setSignInMode}
        onSignedIn={setAccount}
      />
    )
  }

  return (
    <>
      <header className={`session-bar ${account.account_type === 'patient' ? 'patient-session-bar' : ''}`}>
        <div className="workspace-brand"><BrandMark /><strong>Primary Care EMR</strong><span className="workspace-product">{account.account_type === 'patient' ? 'Patient portal' : 'Clinical workspace'}</span></div>
        <div className="session-account"><strong>{account.username}</strong><span>{account.account_type === 'patient' ? 'Patient' : account.staff_role === 'admin' ? 'Administrator' : 'Clinician'}</span></div>
        <button type="button" onClick={() => void signOut()}>
          Sign out
        </button>
      </header>
      {account.account_type === 'patient' ? <PatientPortal /> : <StaffApp isAdmin={account.staff_role === 'admin'} />}
    </>
  )
}

export default App
