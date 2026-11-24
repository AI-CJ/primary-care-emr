import { useEffect, useState } from 'react'
import { API_BASE_URL, apiFetch, getApiErrorMessage } from '../api'
import type { PortalMedicationSummary } from '../types'
import { groupPortalMedications } from '../portalMedicationGroups'

type PortalMedicationsProps = {
  // Staff preview passes chart-scoped summaries; patient sign-in never supplies a patient ID.
  medications?: PortalMedicationSummary[]
}

export default function PortalMedications({ medications }: PortalMedicationsProps) {
  const [loaded, setLoaded] = useState<PortalMedicationSummary[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    if (medications !== undefined) return

    const controller = new AbortController()

    async function loadMedications() {
      setIsLoading(true)
      setError(null)
      setLoaded(null)

      try {
        const response = await apiFetch(API_BASE_URL + '/portal/medications', {
          signal: controller.signal,
        })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: PortalMedicationSummary[] = await response.json()
        if (!controller.signal.aborted) setLoaded(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof TypeError
            ? 'Medications could not be loaded. Check your connection and try again.'
            : requestError instanceof Error
              ? requestError.message
              : 'Medications could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadMedications()
    return () => controller.abort()
  }, [medications, refreshCount])

  const showRecords = medications !== undefined || (!isLoading && !error && loaded !== null)
  const { active, past } = groupPortalMedications(medications ?? loaded ?? [])

  return (
    <section className="portal-card" aria-labelledby="portal-medications">
      <h2 id="portal-medications">My medications</h2>
      <p className="portal-help">
        Medications recorded in your chart. Check with the clinic before changing
        how you take any medication.
      </p>

      {medications === undefined && isLoading && <p role="status">Loading medications...</p>}
      {medications === undefined && error && (
        <div>
          <p role="alert">{error}</p>
          <button
            type="button"
            className="secondary-action-button"
            onClick={() => setRefreshCount((count) => count + 1)}
          >
            Try Again
          </button>
        </div>
      )}

      {showRecords && (
        <>
          {active.length === 0 ? (
            <p>No medications are currently marked as active in your chart.</p>
          ) : (
            <ul className="portal-records">
              {active.map((medication) => (
                <li key={medication.id}>
                  <strong>{medication.name}{medication.strength ? ' · ' + medication.strength : ''}</strong>
                  {medication.dose && <span>Dose: {medication.dose}</span>}
                  {medication.frequency && <span>Frequency: {medication.frequency}</span>}
                  {medication.instructions && <span>Instructions: {medication.instructions}</span>}
                </li>
              ))}
            </ul>
          )}
          {past.length > 0 && (
            <details>
              <summary>Past medications ({past.length})</summary>
              <ul className="portal-records">
                {past.map((medication) => (
                  <li key={medication.id}>
                    <strong>{medication.name}{medication.strength ? ' · ' + medication.strength : ''}</strong>
                    <span>Status: {medication.status === 'completed' ? 'Completed' : 'Discontinued'}</span>
                    {medication.start_date && (
                      <span>Recorded start: <time dateTime={medication.start_date}>
                        {medication.start_date}
                      </time></span>
                    )}
                    {medication.end_date && (
                      <span>Recorded end: <time dateTime={medication.end_date}>
                        {medication.end_date}
                      </time></span>
                    )}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </section>
  )
}
