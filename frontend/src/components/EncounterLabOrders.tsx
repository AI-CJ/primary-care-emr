import { useEffect, useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Encounter, LabOrder, LabOrderInput, LabOrderPriority } from '../types'
import EncounterLabResult from './EncounterLabResult'

type EncounterLabOrdersProps = {
  encounter: Encounter
}

function EncounterLabOrders({ encounter }: EncounterLabOrdersProps) {
  const [orders, setOrders] = useState<LabOrder[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [testName, setTestName] = useState('')
  const [priority, setPriority] = useState<LabOrderPriority>('routine')
  const [clinicalReason, setClinicalReason] = useState('')
  const isFinalized = encounter.finalized_at !== null

  useEffect(() => {
    const controller = new AbortController()

    async function loadOrders() {
      setIsLoading(true)
      setLoadError(null)
      setOrders([])
      try {
        const response = await fetch(
          API_BASE_URL + '/encounters/' + encounter.id + '/lab-orders',
          { signal: controller.signal }
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const records: LabOrder[] = await response.json()
        if (!controller.signal.aborted) setOrders(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setLoadError(
            requestError instanceof Error
              ? requestError.message
              : 'Lab requests could not be loaded.'
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadOrders()
    return () => controller.abort()
  }, [encounter.id])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const name = testName.trim()
    if (!name || isSaving || isFinalized) return

    const orderData: LabOrderInput = {
      test_name: name,
      priority,
      clinical_reason: clinicalReason.trim() || null,
    }

    setIsSaving(true)
    setActionError(null)
    setSuccessMessage(null)
    try {
      const response = await fetch(
        API_BASE_URL + '/encounters/' + encounter.id + '/lab-orders',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(orderData),
        }
      )
      if (!response.ok) {
        setActionError(await getApiErrorMessage(response))
        return
      }
      const saved: LabOrder = await response.json()
      setOrders((current) => [...current, saved])
      setTestName('')
      setPriority('routine')
      setClinicalReason('')
      setSuccessMessage('Lab request recorded for this visit.')
    } catch (requestError) {
      console.error(requestError)
      setActionError('The lab request could not be saved.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section className="encounter-lab-orders" aria-label="Visit lab requests">
      <h3>Lab Requests</h3>
      {isLoading && <p role="status">Loading lab requests...</p>}
      {loadError && <p className="form-error" role="alert">{loadError}</p>}
      {!isLoading && !loadError && (
        <>
          {orders.length === 0 && <p>No lab requests recorded for this visit.</p>}
          {orders.length > 0 && (
            <ul className="encounter-lab-list">
              {orders.map((order) => (
                <li className="encounter-lab-row" key={order.id}>
                  <strong>{order.test_name}</strong>
                  <p className="encounter-meta">
                    {order.priority === 'urgent' ? 'Urgent' : 'Routine'}
                    {order.status === 'resulted' ? ' · Result available · ' : ' · Ordered · '}
                    <time dateTime={order.ordered_at}>
                      {order.ordered_at.slice(0, 16).replace('T', ' ')}
                    </time>
                  </p>
                  {order.clinical_reason && (
                    <p className="encounter-lab-reason">Reason: {order.clinical_reason}</p>
                  )}
                  <EncounterLabResult
                    order={order}
                    visitDate={encounter.visit_date}
                    onRecorded={(orderId) => setOrders((current) => current.map((entry) =>
                      entry.id === orderId ? { ...entry, status: 'resulted' } : entry
                    ))}
                  />
                </li>
              ))}
            </ul>
          )}
          {isFinalized ? (
            <p className="encounter-help">
              New lab requests cannot be added after finalization. Existing requests may still receive results.
            </p>
          ) : (
            <form className="encounter-lab-form" onSubmit={(event) => void handleSubmit(event)}>
              <label className="form-field">
                <span>Lab test name *</span>
                <input
                  type="text"
                  value={testName}
                  onChange={(event) => setTestName(event.target.value)}
                  maxLength={200}
                  required
                  disabled={isSaving}
                />
              </label>
              <label className="form-field">
                <span>Priority</span>
                <select
                  value={priority}
                  onChange={(event) => setPriority(event.target.value as LabOrderPriority)}
                  disabled={isSaving}
                >
                  <option value="routine">Routine</option>
                  <option value="urgent">Urgent</option>
                </select>
              </label>
              <label className="form-field">
                <span>Clinical reason (optional)</span>
                <textarea
                  value={clinicalReason}
                  onChange={(event) => setClinicalReason(event.target.value)}
                  maxLength={1000}
                  rows={2}
                  disabled={isSaving}
                />
              </label>
              <button className="secondary-action-button" type="submit" disabled={isSaving || !testName.trim()}>
                {isSaving ? 'Recording...' : 'Add Lab Request'}
              </button>
            </form>
          )}
          <p className="encounter-help">
            Demo only: use fictional requests. No orders are sent to a laboratory.
          </p>
          {actionError && <p className="form-error" role="alert">{actionError}</p>}
          {successMessage && <p role="status">{successMessage}</p>}
        </>
      )}
    </section>
  )
}

export default EncounterLabOrders
