import DiagnosisIndications from './DiagnosisIndications'
import { useEffect, useRef, useState } from 'react'
import PendingLabActions, { type LabResolution } from './PendingLabActions'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
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
  const [activeOrder, setActiveOrder] = useState<number | null>(null)
  const [notice, setNotice] = useState('')
  const noticeRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => { if (notice) noticeRef.current?.focus() }, [notice])

  function resolved(order: PendingLabOrder, resolution: LabResolution) {
    setOrders(current => current?.filter(item => item.id !== order.id) ?? null)
    setActiveOrder(null)
    setNotice(order.test_name + ' for ' + order.patient_name + (resolution.kind === 'cancelled'
      ? ' cancelled. The request and reason remain in the chart.'
      : ' result recorded. Review and release separately when appropriate.'))
  }

  useEffect(() => {
    const controller = new AbortController()
    queueMicrotask(() => {
      if (controller.signal.aborted) return
      setOrders(null)
      setError(null)
    })

    async function loadOrders() {
      try {
        const response = await apiFetch(
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
              Outstanding requests, with urgent requests first. Record a received result or cancel a request that is no longer needed without leaving this list.
            </p>
          </div>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setRefreshCount((count) => count + 1)}
            disabled={activeOrder !== null || (orders === null && error === null)}
          >
            Refresh
          </button>
        </div>

        {notice && <p role="status" tabIndex={-1} ref={noticeRef} className="lab-resolution-notice">{notice}</p>}
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
                      <DiagnosisIndications records={order.indications} compact />
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
                    <div className="pending-lab-resolution">
                      <PendingLabActions order={order} visitDate={order.visit_date} patientName={order.patient_name}
                        active={activeOrder === order.id} disabled={activeOrder !== null}
                        onBegin={() => { setActiveOrder(order.id); setNotice('') }}
                        onDismiss={() => setActiveOrder(null)}
                        onResolved={resolution => resolved(order, resolution)} />
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
      </section>
    </main>
  )
}

export default PendingLabWorklist
