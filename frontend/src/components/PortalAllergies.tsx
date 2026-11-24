import { useEffect, useState } from 'react'
import { API_BASE_URL, apiFetch, getApiErrorMessage } from '../api'
import type { PortalAllergySummary } from '../types'
import { groupPortalAllergies } from '../portalAllergyGroups'

type PortalAllergiesProps = {
  // Only the staff preview provides chart-scoped data. Patient sign-in uses the session.
  allergies?: PortalAllergySummary[]
}

export default function PortalAllergies({ allergies }: PortalAllergiesProps) {
  const [loaded, setLoaded] = useState<PortalAllergySummary[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    if (allergies !== undefined) return

    const controller = new AbortController()

    async function loadAllergies() {
      setIsLoading(true)
      setError(null)
      setLoaded(null)

      try {
        const response = await apiFetch(API_BASE_URL + '/portal/allergies', {
          signal: controller.signal,
        })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: PortalAllergySummary[] = await response.json()
        if (!controller.signal.aborted) setLoaded(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof TypeError
            ? 'Allergies could not be loaded. Check your connection and try again.'
            : requestError instanceof Error
              ? requestError.message
              : 'Allergies could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadAllergies()
    return () => controller.abort()
  }, [allergies, refreshCount])

  const showRecords = allergies !== undefined || (!isLoading && !error && loaded !== null)
  const { active, inactive } = groupPortalAllergies(allergies ?? loaded ?? [])

  return (
    <section className="portal-card" aria-labelledby="portal-allergies">
      <h2 id="portal-allergies">My allergies</h2>
      <p className="portal-help">
        Allergies recorded in your chart. An empty list does not mean
        you have no allergies.
      </p>

      {allergies === undefined && isLoading && <p role="status">Loading allergies...</p>}
      {allergies === undefined && error && (
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
            <p>No active allergies are listed in your chart. This does not confirm that you have none.</p>
          ) : (
            <ul className="portal-records">
              {active.map((allergy) => (
                <li key={allergy.id}>
                  <strong>{allergy.allergen}</strong>
                  <span>Severity: {allergy.severity}</span>
                  {allergy.reaction && <span>Recorded reaction: {allergy.reaction}</span>}
                </li>
              ))}
            </ul>
          )}
          {inactive.length > 0 && (
            <details>
              <summary>Inactive allergy entries ({inactive.length})</summary>
              <p className="portal-help">
                These entries remain in your chart history. An inactive entry does not confirm
                that an allergy has gone away.
              </p>
              <ul className="portal-records">
                {inactive.map((allergy) => (
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
        </>
      )}
    </section>
  )
}
