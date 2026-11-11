import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { PortalLabOrder, PortalLabResult } from '../types'

type PortalLabResultsProps = {
  patientId: number
}

function PortalLabResults({ patientId }: PortalLabResultsProps) {
  const [orders, setOrders] = useState<PortalLabOrder[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadResults() {
      setIsLoading(true)
      setError(null)
      setOrders(null)

      try {
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/portal-preview/lab-orders',
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: PortalLabOrder[] = await response.json()
        if (!controller.signal.aborted) setOrders(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof TypeError
            ? 'Lab records could not be loaded. Check your connection and try again.'
            : requestError instanceof Error
              ? requestError.message
              : 'Lab records could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadResults()
    return () => controller.abort()
  }, [patientId, refreshCount])

  const pendingRequests = (orders ?? [])
    .filter((order) => order.status === 'ordered')
    .sort((first, second) =>
      second.ordered_at.localeCompare(first.ordered_at) || second.id - first.id)
    .slice(0, 5)

  const recentResults = (orders ?? [])
    .filter((order): order is PortalLabOrder & { result: PortalLabResult } =>
      order.status === 'resulted' && order.result !== null)
    .sort((a, b) =>
      b.result.reported_at.localeCompare(a.result.reported_at) || b.id - a.id)
    .slice(0, 3)

  const cancelledRequests = (orders ?? [])
    .filter((order) => order.status === 'cancelled')
    .sort((first, second) =>
      (second.cancelled_at ?? second.ordered_at).localeCompare(
        first.cancelled_at ?? first.ordered_at) || second.id - first.id)
    .slice(0, 5)

  return (
    <section className="portal-card" aria-labelledby="portal-lab-results">
      <h2 id="portal-lab-results">My lab requests and results</h2>
      <p className="portal-help">
        Recent lab requests, reported results, and cancelled requests from finalized visits in this fictional chart.
        A recorded request does not confirm that a test has been scheduled or collected.
        This preview does not have a patient-release process.
      </p>

      {isLoading && <p role="status">Loading lab records...</p>}
      {error && (
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
      {!isLoading && !error && pendingRequests.length === 0 && recentResults.length === 0 && cancelledRequests.length === 0 && (
        <p>No lab requests or results from finalized visits are available in this preview.</p>
      )}
      {!isLoading && !error && pendingRequests.length > 0 && (
        <div className="portal-lab-group">
          <h3>Requests without results</h3>
          <ul className="portal-records">
            {pendingRequests.map((order) => (
              <li key={order.id}>
                <strong>{order.test_name}</strong>
                <span>
                  Requested <time dateTime={order.ordered_at}>
                    {order.ordered_at.slice(0, 10)}
                  </time>
                </span>
                <span>No result has been recorded in this chart.</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {!isLoading && !error && recentResults.length > 0 && (
        <div className="portal-lab-group">
          <h3>Recent results</h3>
          <ul className="portal-records">
            {recentResults.map((order) => (
              <li key={order.id}>
                <strong>{order.test_name}</strong>
                <span>
                  Reported <time dateTime={order.result.reported_at}>
                    {order.result.reported_at.slice(0, 10)}
                  </time>
                </span>
                <span>
                  Collected <time dateTime={order.result.collected_on}>
                    {order.result.collected_on}
                  </time>
                </span>
                <span>Result: {order.result.result_text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {!isLoading && !error && cancelledRequests.length > 0 && (
        <details className="portal-lab-group">
          <summary>Cancelled requests ({cancelledRequests.length})</summary>
          <p className="portal-help">
            These requests were marked cancelled in this chart. Contact the clinic if you
            still need a test.
          </p>
          <ul className="portal-records">
            {cancelledRequests.map((order) => (
              <li key={order.id}>
                <strong>{order.test_name}</strong>
                <span>
                  Requested <time dateTime={order.ordered_at}>
                    {order.ordered_at.slice(0, 10)}
                  </time>
                </span>
                {order.cancelled_at ? (
                  <span>
                    Recorded as cancelled on <time dateTime={order.cancelled_at}>
                      {order.cancelled_at.slice(0, 10)}
                    </time>
                  </span>
                ) : (
                  <span>Marked cancelled in this chart.</span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}

export default PortalLabResults
