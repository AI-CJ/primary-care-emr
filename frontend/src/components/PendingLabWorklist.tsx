import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { LabOrder } from '../types'

type PendingLabOrder = LabOrder & {
  patient_id: number
  patient_name: string
  visit_date: string
}

type PendingLabWorklistProps = {
  onBack: () => void
  onOpenPatient: (patientId: number) => void
  patientError: string | null
}

function PendingLabWorklist({
  onBack,
  onOpenPatient,
  patientError,
}: PendingLabWorklistProps) {
  const [orders, setOrders] = useState<PendingLabOrder[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setOrders(null)
    setError(null)

    async function loadOrders() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/worklists/pending-lab-orders`,
          { signal: controller.signal },
        )
        if (!response.ok) {
          throw new Error(await getApiErrorMessage(response))
        }

        const records: PendingLabOrder[] = await response.json()
        if (!controller.signal.aborted) setOrders(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(
            requestError instanceof TypeError
              ? 'The server could not be reached. Try again.'
              : requestError instanceof Error
                ? requestError.message
                : 'Pending lab requests could not be loaded.',
          )
        }
      }
    }

    void loadOrders()
    return () => controller.abort()
  }, [refreshCount])

  return (
    <main className="search-page">
      <section className="search-panel schedule-panel" aria-labelledby="pending-labs-heading">
        <button className="back-button" type="button" onClick={onBack}>
          ← Back to patient search
        </button>
        <div className="search-panel-header">
          <div>
            <h1 id="pending-labs-heading">Pending Lab Requests</h1>
            <p className="pending-lab-intro">
              Outstanding requests, with urgent requests first. Open a chart to
              record results or cancel a request.
            </p>
          </div>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setRefreshCount((count) => count + 1)}
            disabled={orders === null && error === null}
          >
            Refresh
          </button>
        </div>

        {patientError && <p className="form-error" role="alert">{patientError}</p>}
        {!orders && !error && (
          <p className="empty-message" role="status">Loading pending requests...</p>
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
        {orders && (
          <>
            <p className="schedule-count" role="status">
              {orders.length} pending request{orders.length === 1 ? '' : 's'}
            </p>
            {orders.length === 0 ? (
              <p className="empty-message">No pending lab requests.</p>
            ) : (
              <ol className="pending-lab-list">
                {orders.map((order) => (
                  <li className="pending-lab-row" key={order.id}>
                    <div>
                      <div className="pending-lab-title">
                        <strong>{order.test_name}</strong>
                        <span className={order.priority === 'urgent'
                          ? 'pending-lab-priority pending-lab-priority-urgent'
                          : 'pending-lab-priority'}>
                          {order.priority === 'urgent' ? 'Urgent' : 'Routine'}
                        </span>
                      </div>
                      <p className="pending-lab-meta">
                        Visit <time dateTime={order.visit_date}>{order.visit_date}</time>
                        {' · '}
                        Ordered <time dateTime={order.ordered_at}>
                          {new Date(order.ordered_at).toLocaleString()}
                        </time>
                        {' · '}
                        Request #{order.id}
                      </p>
                      {order.clinical_reason && (
                        <p className="pending-lab-reason">
                          Reason: {order.clinical_reason}
                        </p>
                      )}
                    </div>
                    <div className="pending-lab-patient">
                      <button
                        className="schedule-patient-link"
                        type="button"
                        onClick={() => onOpenPatient(order.patient_id)}
                      >
                        {order.patient_name}
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
          Synthetic-data demonstration. No requests are transmitted to laboratories.
        </p>
      </section>
    </main>
  )
}

export default PendingLabWorklist
