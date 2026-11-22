import { useEffect, useState } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type { Patient, PortalAllergySummary, PortalCareGoalSummary, PortalMedicationSummary, PortalProblemSummary } from '../types'
import './PatientPortalPreview.css'
import PortalAppointments from './PortalAppointments'
import PortalVisits from './PortalVisits'
import PortalVitals from './PortalVitals'
import PortalLabResults from './PortalLabResults'
import PortalReferrals from './PortalReferrals'
import PortalCareGoals from './PortalCareGoals'
import PortalProblemList from './PortalProblemList'
import PortalMedications from './PortalMedications'

type PatientPortalPreviewProps = {
  patient: Patient
  onBack: () => void
}

type PortalOverview = {
  problems: PortalProblemSummary[]
  medications: PortalMedicationSummary[]
  allergies: PortalAllergySummary[]
  careGoals: PortalCareGoalSummary[]
}

function PatientPortalPreview({ patient, onBack }: PatientPortalPreviewProps) {
  const [overview, setOverview] = useState<PortalOverview | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadRecords<T>(resource: string): Promise<T> {
      const response = await apiFetch(
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
          loadRecords<PortalProblemSummary[]>('portal-preview/problems'),
          loadRecords<PortalMedicationSummary[]>('portal-preview/medications'),
          loadRecords<PortalAllergySummary[]>('portal-preview/allergies'),
          loadRecords<PortalCareGoalSummary[]>('portal-preview/care-goals'),
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

  const activeAllergies = overview?.allergies.filter((item) => item.status === 'active') ?? []
  const inactiveAllergies = overview?.allergies
    .filter((item) => item.status === 'inactive')
    .sort((first, second) =>
      (second.onset_date ?? '').localeCompare(first.onset_date ?? '') || second.id - first.id) ?? []
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
            <PortalProblemList problems={overview.problems} />

            <PortalMedications medications={overview.medications} />

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
              {inactiveAllergies.length > 0 && (
                <details>
                  <summary>Inactive allergy entries ({inactiveAllergies.length})</summary>
                  <p className="portal-help">
                    These entries remain in your chart history. An inactive entry does not confirm
                    that an allergy has gone away.
                  </p>
                  <ul className="portal-records">
                    {inactiveAllergies.map((allergy) => (
                      <li key={allergy.id}>
                        <strong>{allergy.allergen}</strong>
                        <span>Status: Inactive in chart</span>
                        <span>Recorded severity: {allergy.severity}</span>
                        {allergy.reaction && <span>Recorded reaction: {allergy.reaction}</span>}
                        {allergy.onset_date && (
                          <span>
                            Recorded onset: <time dateTime={allergy.onset_date}>
                              {allergy.onset_date}
                            </time>
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </details>
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
