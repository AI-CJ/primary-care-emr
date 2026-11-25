import { useEffect, useState } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type { PortalLabOrder } from '../types'
import { groupPortalLabOrders, type ReleasedOrder } from '../portalLabGroups'
import { formatPortalDate } from '../portalAppointments'
import { portalLabOrdersPath } from '../portalLabOrderRoutes'

type PortalLabResultsProps = {
  // Staff preview supplies a chart ID. Patient sign-in uses the session-scoped route.
  patientId?: number
}

function ReleasedResults({ records }: { records: ReleasedOrder[] }) {
  return <ul className="portal-records portal-released-results">{records.map(order =>
    <li key={order.id}>
      <strong>{order.test_name}</strong>
      <span className="portal-record-status">Shared by the clinic</span>
      <span>Reported <time dateTime={order.result.reported_at}>{formatPortalDate(order.result.reported_at.slice(0,10))}</time></span>
      <span>Collected <time dateTime={order.result.collected_on}>{formatPortalDate(order.result.collected_on)}</time></span>
      <div className="portal-result-text"><strong>Result as recorded</strong><p>{order.result.result_text}</p></div>
    </li>)}</ul>
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
        const response = await apiFetch(
          API_BASE_URL + portalLabOrdersPath(patientId),
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

  const { recent: recentResults, older: olderResults, pending: pendingRequests, awaitingRelease, cancelled: cancelledRequests } = groupPortalLabOrders(orders ?? [])

  return (
    <section className="portal-card" aria-labelledby="portal-lab-results">
      <h2 id="portal-lab-results">My lab requests and results</h2>
      <p className="portal-help">
        Results are shown as recorded by your clinic. Ask your care team about what a result means for you.
        Details appear only after clinic staff share them. A lab request does not confirm that a test has been scheduled or collected.
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
      {!isLoading && !error && pendingRequests.length === 0 && recentResults.length === 0 && olderResults.length === 0 && awaitingRelease.length === 0 && cancelledRequests.length === 0 && (
        <p>No lab requests or results from finalized visits are available.</p>
      )}
      {!isLoading && !error && recentResults.length > 0 && (
        <div className="portal-lab-group">
          <h3>Results shared by your clinic ({recentResults.length + olderResults.length})</h3>
          <ReleasedResults records={recentResults} />
          {olderResults.length > 0 && <details>
            <summary>Earlier results ({olderResults.length})</summary>
            <ReleasedResults records={olderResults} />
          </details>}
        </div>
      )}
      {!isLoading && !error && pendingRequests.length > 0 && (
        <div className="portal-lab-group">
          <h3>Requests without results ({pendingRequests.length})</h3>
          <ul className="portal-records">
            {pendingRequests.map((order) => (
              <li key={order.id}>
                <strong>{order.test_name}</strong>
                <span>
                  Requested <time dateTime={order.ordered_at}>
                    {formatPortalDate(order.ordered_at.slice(0, 10))}
                  </time>
                </span>
                <span className="portal-record-status">No result recorded</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {!isLoading && !error && awaitingRelease.length > 0 && (
        <div className="portal-lab-group">
          <h3>Results not yet shared ({awaitingRelease.length})</h3>
          <p className="portal-help">These results are recorded but are not yet available to patients.</p>
          <ul className="portal-records">
            {awaitingRelease.map((order) => (
              <li key={order.id}>
                <strong>{order.test_name}</strong>
                <span className="portal-record-status">Result not yet released by the clinic.</span>
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
                    {formatPortalDate(order.ordered_at.slice(0, 10))}
                  </time>
                </span>
                {order.cancelled_at ? (
                  <span>
                    Recorded as cancelled on <time dateTime={order.cancelled_at}>
                      {formatPortalDate(order.cancelled_at.slice(0, 10))}
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
