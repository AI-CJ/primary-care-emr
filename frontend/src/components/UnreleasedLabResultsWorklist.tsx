import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { LabResult } from '../types'

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
  const [reviewOrderId, setReviewOrderId] = useState<number | null>(null)
  const [reviewResult, setReviewResult] = useState<LabResult | null>(null)
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [reviewRefreshCount, setReviewRefreshCount] = useState(0)
  const [isReviewLoading, setIsReviewLoading] = useState(false)
  const [releaseConfirmed, setReleaseConfirmed] = useState(false)
  const [isReleasing, setIsReleasing] = useState(false)
  const [releaseError, setReleaseError] = useState<string | null>(null)
  const [releaseMessage, setReleaseMessage] = useState<string | null>(null)

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

  useEffect(() => {
    if (reviewOrderId === null) return

    const controller = new AbortController()
    setReviewResult(null)
    setReviewError(null)
    setReleaseError(null)
    setReleaseConfirmed(false)
    setIsReviewLoading(true)

    async function loadResult() {
      try {
        const response = await fetch(
          API_BASE_URL + '/lab-orders/' + reviewOrderId + '/result',
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const record: LabResult = await response.json()
        if (!controller.signal.aborted) setReviewResult(record)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setReviewError(
            requestError instanceof TypeError
              ? 'The server could not be reached. Try again.'
              : requestError instanceof Error
                ? requestError.message
                : 'The lab result could not be loaded.',
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsReviewLoading(false)
      }
    }

    void loadResult()
    return () => controller.abort()
  }, [reviewOrderId, reviewRefreshCount])

  function refreshResults() {
    setReviewOrderId(null)
    setReviewResult(null)
    setReleaseMessage(null)
    setRefreshCount((count) => count + 1)
  }

  async function handleRelease(order: UnreleasedLabResult) {
    if (
      isReleasing || !releaseConfirmed || !reviewResult ||
      reviewResult.lab_order_id !== order.order_id ||
      reviewResult.released_at !== null
    ) return

    if (!window.confirm(
      'Release this lab result to the patient portal preview? This cannot be undone.',
    )) return

    setIsReleasing(true)
    setReleaseError(null)

    try {
      const response = await fetch(
        API_BASE_URL + '/lab-orders/' + order.order_id + '/result/release',
        { method: 'POST' },
      )
      if (!response.ok) {
        setReleaseError(await getApiErrorMessage(response))
        return
      }

      const released: LabResult = await response.json()
      if (released.lab_order_id !== order.order_id || !released.released_at) {
        setReleaseError('The server did not confirm the release. Refresh the worklist.')
        return
      }

      setResults((current) => current?.filter((item) => item.order_id !== order.order_id) ?? null)
      setReviewOrderId(null)
      setReviewResult(null)
      setReleaseMessage(order.test_name + ' released to the portal preview for ' + order.patient_name + '.')
    } catch (requestError) {
      setReleaseError(requestError instanceof Error
        ? requestError.message
        : 'The lab result could not be released.')
    } finally {
      setIsReleasing(false)
    }
  }

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
              Review the result before releasing it to the portal preview. Open the patient chart for clinical context.
            </p>
          </div>
          <button
            className="secondary-action-button"
            type="button"
            onClick={refreshResults}
            disabled={isReleasing || (results === null && error === null)}
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
              onClick={refreshResults}
            >
              Try Again
            </button>
          </div>
        )}
        {releaseMessage && <p role="status">{releaseMessage}</p>}
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
                      <button
                        type="button"
                        className="secondary-action-button"
                        aria-expanded={reviewOrderId === result.order_id}
                        aria-controls={'lab-review-' + result.order_id}
                        disabled={isReleasing}
                        onClick={() => {
                          setReleaseError(null)
                          setReviewOrderId((current) =>
                            current === result.order_id ? null : result.order_id)
                        }}
                      >
                        {reviewOrderId === result.order_id ? 'Hide result' : 'Review result'}
                      </button>
                      {reviewOrderId === result.order_id && (
                        <div id={'lab-review-' + result.order_id} className="patient-lab-result">
                          {isReviewLoading && <p role="status">Loading lab result...</p>}
                          {reviewError && (
                            <div>
                              <p className="form-error" role="alert">{reviewError}</p>
                              <button
                                type="button"
                                className="secondary-action-button"
                                onClick={() => setReviewRefreshCount((count) => count + 1)}
                              >
                                Try Again
                              </button>
                            </div>
                          )}
                          {!isReviewLoading && !reviewError &&
                            reviewResult?.lab_order_id === result.order_id && (
                            <>
                              <p className="encounter-meta">
                                Collected <time dateTime={reviewResult.collected_on}>
                                  {reviewResult.collected_on}
                                </time>
                                {' · '}
                                Reported <time dateTime={reviewResult.reported_at}>
                                  {new Date(reviewResult.reported_at).toLocaleString()}
                                </time>
                              </p>
                              <p className="pending-lab-reason">{reviewResult.result_text}</p>
                              {reviewResult.released_at ? (
                                <p role="status">
                                  This result has already been released. Refresh the worklist.
                                </p>
                              ) : (
                                <>
                                  <label className="encounter-release-confirmation">
                                    <input
                                      type="checkbox"
                                      checked={releaseConfirmed}
                                      disabled={isReleasing}
                                      onChange={(event) => setReleaseConfirmed(event.target.checked)}
                                    />
                                    <span>
                                      I reviewed this result and confirmed it is appropriate
                                      to share in the patient portal preview.
                                    </span>
                                  </label>
                                  <button
                                    type="button"
                                    className="secondary-action-button"
                                    disabled={!releaseConfirmed || isReleasing}
                                    onClick={() => void handleRelease(result)}
                                  >
                                    {isReleasing ? 'Releasing...' : 'Release to Portal Preview'}
                                  </button>
                                </>
                              )}
                              {releaseError && <p className="form-error" role="alert">{releaseError}</p>}
                            </>
                          )}
                        </div>
                      )}
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
