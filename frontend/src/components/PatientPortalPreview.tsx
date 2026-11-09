import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Allergy, CareGoal, Medication, Patient, Problem } from '../types'
import './PatientPortalPreview.css'
import PortalAppointments from './PortalAppointments'
import PortalVisits from './PortalVisits'
import PortalVitals from './PortalVitals'
import PortalLabResults from './PortalLabResults'
import PortalReferrals from './PortalReferrals'
import PortalCareGoals from './PortalCareGoals'

type PatientPortalPreviewProps = {
  patient: Patient
  onBack: () => void
}

type PortalOverview = {
  problems: Problem[]
  medications: Medication[]
  allergies: Allergy[]
  careGoals: CareGoal[]
}

function PatientPortalPreview({ patient, onBack }: PatientPortalPreviewProps) {
  const [overview, setOverview] = useState<PortalOverview | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadRecords<T>(resource: string): Promise<T> {
      const response = await fetch(
        API_BASE_URL + '/patients/' + patient.id + '/' + resource,
        { signal: controller.signal },
      )
      if (!response.ok) throw new Error(await getApiErrorMessage(response))
      return response.json() as Promise<T>
    }

    async function loadOverview() {
      setIsLoading(true)
      setError(null)
      setOverview(null)

      try {
        const [problems, medications, allergies, careGoals] = await Promise.all([
          loadRecords<Problem[]>('problems'),
          loadRecords<Medication[]>('medications'),
          loadRecords<Allergy[]>('allergies'),
          loadRecords<CareGoal[]>('care-goals'),
        ])
        if (!controller.signal.aborted) {
          setOverview({ problems, medications, allergies, careGoals })
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof Error
            ? requestError.message
            : 'Your health summary could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadOverview()
    return () => controller.abort()
  }, [patient.id, reloadCount])

  const activeProblems = overview?.problems.filter((item) => item.status === 'active') ?? []
  const activeMedications = overview?.medications.filter((item) => item.status === 'active') ?? []
  const activeAllergies = overview?.allergies.filter((item) => item.status === 'active') ?? []
  const displayName = patient.preferred_name || patient.first_name

  return (
    <main className="portal-preview">
      <div className="portal-shell">
        <button type="button" className="back-button" onClick={onBack}>
          ← Back to staff chart
        </button>
        <header className="portal-header">
          <p className="portal-eyebrow">Patient portal preview</p>
          <h1>Welcome, {displayName}</h1>
          <p>Here's a summary of the information on your chart.</p>
        </header>
        <p className="portal-disclaimer" role="note">
          This is a staff preview using fictional patient data. It is not a patient login
          or a secure portal. Do not use it with real medical information.
        </p>

        {isLoading && <p role="status">Loading health summary...</p>}
        {error && (
          <div className="portal-message">
            <p role="alert">{error}</p>
            <button
              type="button"
              className="secondary-action-button"
              onClick={() => setReloadCount((count) => count + 1)}
            >
              Try Again
            </button>
          </div>
        )}

        {!isLoading && overview && (
          <div className="portal-grid">
            <PortalAppointments key={patient.id} patientId={patient.id} />
            <PortalVisits patientId={patient.id} />
            <PortalVitals key={patient.id} patientId={patient.id} />
            <PortalLabResults key={patient.id} patientId={patient.id} />
            <PortalReferrals patientId={patient.id} />
            <section className="portal-card" aria-labelledby="portal-conditions">
              <h2 id="portal-conditions">My health conditions</h2>
              {activeProblems.length === 0 ? (
                <p>No active conditions are listed in your chart.</p>
              ) : (
                <ul className="portal-records">
                  {activeProblems.map((problem) => (
                    <li key={problem.id}>
                      <strong>{problem.name}</strong>
                      {problem.onset_date && <span>Noted since {problem.onset_date}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="portal-card" aria-labelledby="portal-medications">
              <h2 id="portal-medications">My medications</h2>
              <p className="portal-help">Medications currently listed as active.</p>
              {activeMedications.length === 0 ? (
                <p>No active medications are listed in your chart.</p>
              ) : (
                <ul className="portal-records">
                  {activeMedications.map((medication) => (
                    <li key={medication.id}>
                      <strong>{medication.name}{medication.strength ? ' · ' + medication.strength : ''}</strong>
                      {medication.dose && <span>Dose: {medication.dose}</span>}
                      {medication.frequency && <span>Frequency: {medication.frequency}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="portal-card" aria-labelledby="portal-allergies">
              <h2 id="portal-allergies">My allergies</h2>
              {activeAllergies.length === 0 ? (
                <p>No active allergies are listed in your chart. This does not confirm that you have none.</p>
              ) : (
                <ul className="portal-records">
                  {activeAllergies.map((allergy) => (
                    <li key={allergy.id}>
                      <strong>{allergy.allergen}</strong>
                      <span>Severity: {allergy.severity}</span>
                      {allergy.reaction && <span>Recorded reaction: {allergy.reaction}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <PortalCareGoals goals={overview.careGoals} />
          </div>
        )}
      </div>
    </main>
  )
}

export default PatientPortalPreview
