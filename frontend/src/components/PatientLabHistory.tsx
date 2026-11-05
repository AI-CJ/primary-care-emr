import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { PatientLabOrder } from '../types'

type PatientLabHistoryProps = {
  patientId: number
}

const statusLabels: Record<PatientLabOrder['status'], string> = {
  ordered: 'Pending',
  resulted: 'Resulted',
  cancelled: 'Cancelled',
}

function PatientLabHistory({ patientId }: PatientLabHistoryProps) {
  const [orders, setOrders] = useState<PatientLabOrder[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadOrders() {
      setIsLoading(true)
      setError(null)
      setOrders([])

      try {
        const response = await fetch(
          `${API_BASE_URL}/patients/${patientId}/lab-orders`,
          { signal: controller.signal }
        )
        if (!response.ok) {
          throw new Error(await getApiErrorMessage(response))
        }
        const records: PatientLabOrder[] = await response.json()
        if (!controller.signal.aborted) setOrders(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Lab history could not be loaded.'
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadOrders()
    return () => controller.abort()
  }, [patientId, reloadCount])

  return (
    <section className="overview-card patient-lab-card" aria-labelledby="patient-lab-heading">
      <div className="overview-card-header">
        <h2 id="patient-lab-heading">Lab History</h2>
        <button
          className="secondary-action-button"
          type="button"
          disabled={isLoading}
          onClick={() => setReloadCount((count) => count + 1)}
        >
          Refresh
        </button>
      </div>

      {isLoading && <p role="status">Loading lab history...</p>}
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
      {!isLoading && !error && orders.length === 0 && (
        <p>No lab requests recorded for this patient.</p>
      )}
      {!isLoading && !error && orders.length > 0 && (
        <ul className="patient-lab-list">
          {orders.map((order) => (
            <li className="patient-lab-row" key={order.id}>
              <div className="patient-lab-row-header">
                <strong>{order.test_name}</strong>
                <span className="patient-lab-status">{statusLabels[order.status]}</span>
              </div>
              <p className="encounter-meta">
                Visit <time dateTime={order.visit_date}>{order.visit_date}</time>
                {' · '}
                {order.priority === 'urgent' ? 'Urgent' : 'Routine'}
                {' · '}
                Request #{order.id}
              </p>
              {order.clinical_reason && (
                <p className="patient-lab-details">
                  Reason: {order.clinical_reason}
                </p>
              )}
              {order.status === 'cancelled' && (
                <p className="patient-lab-details">
                  Cancelled: {order.cancellation_reason ?? 'Reason not recorded'}
                </p>
              )}
              {order.result && (
                <div className="patient-lab-result">
                  <strong>Result</strong>
                  <p className="encounter-meta">
                    Collected <time dateTime={order.result.collected_on}>
                      {order.result.collected_on}
                    </time>
                    {' · '}
                    Reported <time dateTime={order.result.reported_at}>
                      {order.result.reported_at.slice(0, 10)}
                    </time>
                  </p>
                  <p className="patient-lab-details">{order.result.result_text}</p>
                </div>
              )}
              {order.status === 'resulted' && !order.result && (
                <p>Result details are unavailable.</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default PatientLabHistory
