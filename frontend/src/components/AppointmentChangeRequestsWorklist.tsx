import { useEffect, useState } from 'react'
import { API_BASE_URL, apiFetch, getApiErrorMessage } from '../api'
import type { StaffAppointmentChangeRequest } from '../types'

type Props = {
  onBack: () => void
  onOpenPatient: (patientId: number, appointmentId: number) => void
  patientError: string | null
}

export default function AppointmentChangeRequestsWorklist({
  onBack, onOpenPatient, patientError,
}: Props) {
  const [requests, setRequests] = useState<StaffAppointmentChangeRequest[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [refresh, setRefresh] = useState(0)
  const [reviewingId, setReviewingId] = useState<number | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    queueMicrotask(() => {
      if (!controller.signal.aborted) { setRequests(null); setError(null) }
    })
    async function load() {
      try {
        const response = await apiFetch(
          API_BASE_URL + '/worklists/appointment-change-requests', { signal: controller.signal })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const records: StaffAppointmentChangeRequest[] = await response.json()
        if (!controller.signal.aborted) setRequests(records)
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof TypeError
          ? 'Unable to reach the server. Try again.'
          : reason instanceof Error ? reason.message : 'Unable to load requests.')
      }
    }
    void load()
    return () => controller.abort()
  }, [refresh])

  async function review(request: StaffAppointmentChangeRequest) {
    if (reviewingId !== null || !window.confirm(
      'Mark request #' + request.id + ' reviewed? This only acknowledges it. ' +
      'It does NOT change the appointment. Make any scheduling change separately in the chart.'
    )) return
    setReviewingId(request.id)
    setActionError(null)
    setNotice(null)
    try {
      const response = await apiFetch(
        API_BASE_URL + '/appointment-change-requests/' + request.id + '/review',
        { method: 'POST' })
      if (!response.ok) throw new Error(await getApiErrorMessage(response))
      setRequests((current) => current?.filter((item) => item.id !== request.id) ?? null)
      setNotice('Request #' + request.id + ' acknowledged. Verify the schedule separately.')
    } catch (reason) {
      setActionError(reason instanceof TypeError ? 'Unable to reach the server. Try again.'
        : reason instanceof Error ? reason.message : 'Unable to review the request.')
    } finally {
      setReviewingId(null)
    }
  }

  return (
    <main className="search-page">
      <section className="search-panel schedule-panel" aria-labelledby="change-worklist-heading">
        <button type="button" className="back-button" onClick={onBack}>
          ← Back to patient search
        </button>
        <div className="search-panel-header">
          <div>
            <h1 id="change-worklist-heading">Appointment change requests</h1>
            <p className="pending-lab-intro">
              Review patient requests. Open the chart to make any scheduling changes.
              Marking a request reviewed only acknowledges it.
            </p>
          </div>
          <button type="button" className="secondary-action-button"
            disabled={reviewingId !== null}
            onClick={() => { setNotice(null); setActionError(null); setRefresh((value) => value + 1) }}>
            Refresh
          </button>
        </div>
        {patientError && <p role="alert" className="form-error">{patientError}</p>}
        {actionError && <p role="alert" className="form-error">{actionError}</p>}
        {notice && <p role="status">{notice}</p>}
        {!requests && !error && <p role="status">Loading appointment requests...</p>}
        {error && <div>
          <p role="alert" className="form-error">{error}</p>
          <button type="button" className="secondary-action-button"
            onClick={() => setRefresh((value) => value + 1)}>Try Again</button>
        </div>}
        {requests && <>
          <p role="status" className="schedule-count">
            {requests.length} pending request{requests.length === 1 ? '' : 's'}
          </p>
          {requests.length === 0 ? <p>No pending appointment change requests.</p> : (
            <ol className="pending-lab-list">
              {requests.map((request) => <li key={request.id} className="pending-lab-row">
                <div>
                  <div className="pending-lab-title">
                    <strong>{request.kind === 'cancel' ? 'Cancellation' : 'Rescheduling'} request</strong>
                    <span className="pending-lab-priority">Pending</span>
                  </div>
                  <p className="pending-lab-meta">
                    Patient #{request.patient_id} {' · '}Appointment #{request.appointment_id}
                    {' · '}Sent <time dateTime={request.created_at}>
                      {new Date(request.created_at).toLocaleString()}
                    </time>
                  </p>
                </div>
                <div className="pending-lab-patient">
                  <button type="button" className="schedule-patient-link"
                    onClick={() => onOpenPatient(request.patient_id, request.appointment_id)}>
                    Open appointment in chart
                  </button>
                  <button type="button" className="secondary-action-button"
                    disabled={reviewingId !== null} onClick={() => void review(request)}>
                    {reviewingId === request.id ? 'Recording...' : 'Mark reviewed'}
                  </button>
                </div>
              </li>)}
            </ol>
          )}
        </>}
        <p className="pending-lab-disclaimer">
          Synthetic records only. Acknowledgment does not cancel or reschedule a visit.
        </p>
      </section>
    </main>
  )
}
