import { useEffect, useState } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type { Patient, PortalAllergySummary, PortalCareGoalSummary, PortalMedicationSummary, PortalProblemSummary } from '../types'
import './PatientPortalPreview.css'
import SectionNavigation from './SectionNavigation'
import { type PortalSection, portalSections } from '../portalNavigation'
import PortalAppointments from './PortalAppointments'
import PortalHome from './PortalHome'
import PortalVisits from './PortalVisits'
import PortalVitals from './PortalVitals'
import PortalLabResults from './PortalLabResults'
import PortalReferrals from './PortalReferrals'
import PortalCareGoals from './PortalCareGoals'
import PortalProblemList from './PortalProblemList'
import PortalMedications from './PortalMedications'
import PortalAllergies from './PortalAllergies'

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
  const [section, setSection] = useState<PortalSection>('health')
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
        <p className="portal-help">Staff preview of the patient view. You remain signed in as staff.</p>

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

        <SectionNavigation label="Patient portal preview sections"
          options={portalSections.filter((option) => option.id !== 'preferences')}
          current={section} onChange={setSection} />

        {section === 'home' && <PortalHome patientId={patient.id} onNavigate={setSection} />}
        {section !== 'home' && !isLoading && overview && (
          <div className="portal-grid" key={section}>
            {section === 'health' && <>
              <PortalProblemList problems={overview.problems} />
              <PortalMedications medications={overview.medications} />
              <PortalAllergies allergies={overview.allergies} />
              <PortalVitals key={patient.id} patientId={patient.id} />
            </>}
            {section === 'visits' && <>
              <PortalAppointments key={patient.id} patientId={patient.id} />
              <PortalVisits patientId={patient.id} />
            </>}
            {section === 'results' && <>
              <PortalLabResults key={patient.id} patientId={patient.id} />
              <PortalReferrals patientId={patient.id} />
            </>}
            {section === 'care' && <PortalCareGoals goals={overview.careGoals} />}
          </div>
        )}
      </div>
    </main>
  )
}

export default PatientPortalPreview
