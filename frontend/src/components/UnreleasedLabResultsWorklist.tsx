import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'

type UnreleasedLabResult = {
  order_id: number
  patient_id: number
  patient_name: string
  test_name: string
  priority: 'routine' | 'urgent'
  visit_date: string
  ordered_at: string
  reported_at: string
}

type UnreleasedLabResultsWorklistProps = {
  onBack: () => void
  onOpenPatient: (patientId: number) => void
  patientError: string | null
}

function UnreleasedLabResultsWorklist({
  onBack,
  onOpenPatient,
  patientError,
}: UnreleasedLabResultsWorklistProps) {
  const [results, setResults] = useState<UnreleasedLabResult[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setResults(null)
    setError(null)

    async function loadResults() {
      try {
        const response = await fetch(
          API_BASE_URL + '/worklists/unreleased-lab-results',
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: UnreleasedLabResult[] = await response.json()
        if (!controller.signal.aborted) setResults(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(
            requestError instanceof TypeError
              ? 'The server could not be reached. Try again.'
              : requestError instanceof Error
                ? requestError.message
                : 'Results awaiting release could not be loaded.',
          )
        }
      }
    }

    void loadResults()
    return () => controller.abort()
  }, [refreshCount])

  return (
    <main className="search-page">
      <section className="search-panel schedule-panel" aria-labelledby="unreleased-labs-heading">
        <button className="back-button" type="button" onClick={onBack}>
          ← Back to patient search
        </button>
        <div className="search-panel-header">
          <div>
            <h1 id="unreleased-labs-heading">Lab Results to Release</h1>
            <p className="pending-lab-intro">
              Recorded results from finalized visits awaiting staff release, with urgent requests first.
              Open a chart to review the result before releasing it to the portal preview.
            </p>
          </div>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setRefreshCount((count) => count + 1)}
            disabled={results === null && error === null}
          >
            Refresh
          </button>
        </div>

        {patientError && <p className="form-error" role="alert">{patientError}</p>}
        {!results && !error && (
          <p className="empty-message" role="status">Loading results awaiting release...</p>
        )}
        {error && (
          <div>
            <p className="form-error" role="alert">{error}</p>
            <button
              className="secondary-action-button"
              type="button"
              onClick={() => setRefreshCount((count) => count + 1)}
            >
              Try Again
            </button>
          </div>
        )}
        {results && (
          <>
            <p className="schedule-count" role="status">
              {results.length} result{results.length === 1 ? '' : 's'} awaiting release
            </p>
            {results.length === 0 ? (
              <p className="empty-message">No lab results are awaiting release.</p>
            ) : (
              <ol className="pending-lab-list">
                {results.map((result) => (
                  <li className="pending-lab-row" key={result.order_id}>
                    <div>
                      <div className="pending-lab-title">
                        <strong>{result.test_name}</strong>
                        <span className={result.priority === 'urgent'
                          ? 'pending-lab-priority pending-lab-priority-urgent'
                          : 'pending-lab-priority'}>
                          {result.priority === 'urgent' ? 'Urgent' : 'Routine'}
                        </span>
                      </div>
                      <p className="pending-lab-meta">
                        Visit <time dateTime={result.visit_date}>{result.visit_date}</time>
                        {' · '}
                        Reported <time dateTime={result.reported_at}>
                          {new Date(result.reported_at).toLocaleString()}
                        </time>
                        {' · '}
                        Request #{result.order_id}
                      </p>
                    </div>
                    <div className="pending-lab-patient">
                      <button
                        className="schedule-patient-link"
                        type="button"
                        onClick={() => onOpenPatient(result.patient_id)}
                      >
                        {result.patient_name}
                      </button>
                      <span>Open patient chart</span>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
        <p className="pending-lab-disclaimer">
          Synthetic-data demonstration. Results are not transmitted to patients or laboratories.
        </p>
      </section>
    </main>
  )
}

export default UnreleasedLabResultsWorklist
