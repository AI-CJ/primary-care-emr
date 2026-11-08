import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { PatientTimelineEntry } from '../types'

type PatientTimelineProps = {
  patientId: number
}

const activityLabels: Record<PatientTimelineEntry['kind'], string> = {
  visit: 'Visit',
  vitals: 'Vital signs',
  lab_order: 'Lab request',
  lab_result: 'Lab result',
  referral: 'Referral',
  care_goal: 'Care goal',
  follow_up: 'Follow-up task',
}

function PatientTimeline({ patientId }: PatientTimelineProps) {
  const [entries, setEntries] = useState<PatientTimelineEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadTimeline() {
      setIsLoading(true)
      setError(null)
      setEntries([])

      try {
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/timeline?limit=50',
          { signal: controller.signal },
        )
        if (!response.ok) {
          throw new Error(await getApiErrorMessage(response))
        }
        const records: PatientTimelineEntry[] = await response.json()
        if (!controller.signal.aborted) setEntries(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Clinical activity could not be loaded.',
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadTimeline()
    return () => controller.abort()
  }, [patientId, reloadCount])

  return (
    <section className="overview-card patient-timeline-card" aria-labelledby="patient-timeline-heading">
      <div className="overview-card-header">
        <h2 id="patient-timeline-heading">Clinical Activity</h2>
        <button
          className="secondary-action-button"
          type="button"
          disabled={isLoading}
          onClick={() => setReloadCount((count) => count + 1)}
        >
          Refresh
        </button>
      </div>
      <p className="patient-timeline-help">
        A dated summary of chart records, not an audit trail. Refresh to see recent changes.
      </p>

      {isLoading && <p role="status">Loading clinical activity...</p>}
      {error && (
        <div>
          <p className="form-error" role="alert">{error}</p>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setReloadCount((count) => count + 1)}
          >
            Try Again
          </button>
        </div>
      )}
      {!isLoading && !error && entries.length === 0 && (
        <p>No clinical activity recorded for this patient.</p>
      )}
      {!isLoading && !error && entries.length > 0 && (
        <>
          <ol className="patient-timeline-list">
            {entries.map((entry) => (
              <li className="patient-timeline-row" key={entry.kind + '-' + entry.record_id}>
                <time dateTime={entry.occurred_on}>{entry.occurred_on}</time>
                <div className="patient-timeline-detail">
                  <span className="patient-timeline-kind">{activityLabels[entry.kind]}</span>
                  <strong>{entry.title}</strong>
                  <span className="patient-timeline-status">{entry.status.replaceAll('_', ' ')}</span>
                </div>
              </li>
            ))}
          </ol>
          {entries.length === 50 && (
            <p className="patient-timeline-help">Showing the 50 most recent records.</p>
          )}
        </>
      )}
    </section>
  )
}

export default PatientTimeline
