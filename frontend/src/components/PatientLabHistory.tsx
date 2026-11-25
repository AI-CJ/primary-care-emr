import DiagnosisIndications from './DiagnosisIndications'
import { useEffect, useRef, useState } from 'react'
import PendingLabActions, { type LabResolution } from './PendingLabActions'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type { PatientLabOrder } from '../types'

type PatientLabHistoryProps = {
  patientId: number
  archived?: boolean
}

const statusLabels: Record<PatientLabOrder['status'], string> = {
  ordered: 'Pending',
  resulted: 'Resulted',
  cancelled: 'Cancelled',
}

function PatientLabHistory({ patientId, archived = false }: PatientLabHistoryProps) {
  const [orders, setOrders] = useState<PatientLabOrder[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadCount, setReloadCount] = useState(0)
  const [activeOrder, setActiveOrder] = useState<number | null>(null)
  const [notice, setNotice] = useState('')
  const noticeRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => { if (notice) noticeRef.current?.focus() }, [notice])

  function resolved(order: PatientLabOrder, resolution: LabResolution) {
    setOrders(current => current.map(item => item.id !== order.id ? item : resolution.kind === 'cancelled'
      ? { ...item, ...resolution.order }
      : { ...item, status: 'resulted', result: resolution.result }))
    setActiveOrder(null)
    setNotice(order.test_name + (resolution.kind === 'cancelled'
      ? ' cancelled. The request and reason remain in the chart.'
      : ' result recorded. Review and release separately when appropriate.'))
  }

  useEffect(() => {
    const controller = new AbortController()

    async function loadOrders() {
      setIsLoading(true)
      setError(null)
      setOrders([])

      try {
        const response = await apiFetch(
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
          disabled={isLoading || activeOrder !== null}
          onClick={() => setReloadCount((count) => count + 1)}
        >
          Refresh
        </button>
      </div>

      {notice && <p role="status" tabIndex={-1} ref={noticeRef} className="lab-resolution-notice">{notice}</p>}
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
              <DiagnosisIndications records={order.indications} />
              {order.clinical_reason && (
                <p className="patient-lab-details">
                  Reason: {order.clinical_reason}
                </p>
              )}
              {order.status === 'cancelled' && (
                <p className="patient-lab-details">
                  Cancelled: {order.cancellation_reason ?? 'Reason not recorded'}
                  {order.cancelled_at && <> · <time dateTime={order.cancelled_at}>{order.cancelled_at.slice(0, 10)}</time></>}
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
                  <p className="encounter-meta">
                    {order.result.released_at ? (
                      <>
                        Released to portal preview{' '}
                        <time dateTime={order.result.released_at}>
                          {new Date(order.result.released_at).toLocaleString()}
                        </time>
                      </>
                    ) : (
                      'Not released to portal preview.'
                    )}
                  </p>
                </div>
              )}
              {order.status === 'ordered' && !archived && (
                <PendingLabActions order={order} visitDate={order.visit_date}
                  active={activeOrder === order.id} disabled={activeOrder !== null}
                  onBegin={() => { setActiveOrder(order.id); setNotice('') }}
                  onDismiss={() => setActiveOrder(null)} onResolved={resolution => resolved(order, resolution)} />
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
