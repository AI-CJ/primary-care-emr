import { useEffect, useState } from 'react'
import { API_BASE_URL, apiFetch, getApiErrorMessage } from '../api'
import type { PortalProblemSummary } from '../types'

type PortalProblemListProps = {
  // Staff preview supplies its own chart data; patient sign-in never supplies a patient ID.
  problems?: PortalProblemSummary[]
}

export default function PortalProblemList({ problems }: PortalProblemListProps) {
  const [loaded, setLoaded] = useState<PortalProblemSummary[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    if (problems !== undefined) return

    const controller = new AbortController()

    async function loadProblems() {
      setIsLoading(true)
      setError(null)
      setLoaded(null)

      try {
        const response = await apiFetch(API_BASE_URL + '/portal/problems', {
          signal: controller.signal,
        })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: PortalProblemSummary[] = await response.json()
        if (!controller.signal.aborted) setLoaded(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof TypeError
            ? 'Conditions could not be loaded. Check your connection and try again.'
            : requestError instanceof Error
              ? requestError.message
              : 'Conditions could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadProblems()
    return () => controller.abort()
  }, [problems, refreshCount])

  const showRecords = problems !== undefined || (!isLoading && !error && loaded !== null)
  const records = problems ?? loaded ?? []
  const activeProblems = records.filter((problem) => problem.status === 'active')
  const resolvedProblems = records
    .filter((problem) => problem.status === 'resolved')
    .sort((first, second) =>
      (second.resolved_date ?? second.onset_date ?? '').localeCompare(
        first.resolved_date ?? first.onset_date ?? '',
      ) || second.id - first.id)

  return (
    <section className="portal-card" aria-labelledby="portal-conditions">
      <h2 id="portal-conditions">My health conditions</h2>

      {problems === undefined && isLoading && <p role="status">Loading conditions...</p>}
      {problems === undefined && error && (
        <div>
          <p role="alert">{error}</p>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setRefreshCount((count) => count + 1)}
          >
            Try Again
          </button>
        </div>
      )}

      {showRecords && (
        <>
          {activeProblems.length === 0 ? (
            <p>No active conditions are listed in your chart.</p>
          ) : (
            <ul className="portal-records">
              {activeProblems.map((problem) => (
                <li key={problem.id}>
                  <strong>{problem.name}</strong>
                  {problem.onset_date && (
                    <span>Noted since <time dateTime={problem.onset_date}>
                      {problem.onset_date}
                    </time></span>
                  )}
                </li>
              ))}
            </ul>
          )}
          {resolvedProblems.length > 0 && (
            <details>
              <summary>Past conditions ({resolvedProblems.length})</summary>
              <ul className="portal-records">
                {resolvedProblems.map((problem) => (
                  <li key={problem.id}>
                    <strong>{problem.name}</strong>
                    <span>Status: Resolved</span>
                    {problem.onset_date && (
                      <span>Recorded onset: <time dateTime={problem.onset_date}>
                        {problem.onset_date}
                      </time></span>
                    )}
                    {problem.resolved_date && (
                      <span>Recorded resolved date: <time dateTime={problem.resolved_date}>
                        {problem.resolved_date}
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
