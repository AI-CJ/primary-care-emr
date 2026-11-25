import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { API_BASE_URL, apiFetch, getApiErrorMessage } from '../api'
import { requestableAppointments } from '../appointmentChangeRequests'
import { localDate } from '../date'
import { formatPortalAppointment } from '../portalAppointments'
import type { AppointmentChangeRequest, PortalAppointmentSummary } from '../types'

type Data = { appointments: PortalAppointmentSummary[], requests: AppointmentChangeRequest[] }
const endpoint = API_BASE_URL + '/portal/appointment-change-requests'

export default function PortalAppointmentChangeRequests() {
  const [data, setData] = useState<Data | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [refresh, setRefresh] = useState(0)
  const [appointmentId, setAppointmentId] = useState('')
  const [kind, setKind] = useState<'cancel' | 'reschedule'>('reschedule')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    queueMicrotask(() => {
      if (!controller.signal.aborted) { setData(null); setError(null) }
    })
    async function load() {
      try {
        const [appointmentsResponse, requestsResponse] = await Promise.all([
          apiFetch(API_BASE_URL + '/portal/appointments', { signal: controller.signal }),
          apiFetch(endpoint, { signal: controller.signal }),
        ])
        if (!appointmentsResponse.ok) throw new Error(await getApiErrorMessage(appointmentsResponse))
        if (!requestsResponse.ok) throw new Error(await getApiErrorMessage(requestsResponse))
        const [appointments, requests]: [PortalAppointmentSummary[], AppointmentChangeRequest[]] =
          await Promise.all([appointmentsResponse.json(), requestsResponse.json()])
        if (!controller.signal.aborted) setData({ appointments, requests })
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof TypeError
          ? 'Unable to reach the server. Try again.'
          : reason instanceof Error ? reason.message : 'Unable to load requests.')
      }
    }
    void load()
    return () => controller.abort()
  }, [refresh])

  const eligible = data ? requestableAppointments(data.appointments, data.requests, localDate()) : []
  const selected = eligible.find((item) => String(item.id) === appointmentId)
  const byId = new Map(data?.appointments.map((item) => [item.id, item]) ?? [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected || saving) return
    setSaving(true)
    setActionError(null)
    setNotice(null)
    try {
      const response = await apiFetch(endpoint, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appointment_id: selected.id, kind }),
      })
      if (!response.ok) throw new Error(await getApiErrorMessage(response))
      const request: AppointmentChangeRequest = await response.json()
      setData((current) => current ? { ...current, requests: [request, ...current.requests] } : current)
      setAppointmentId('')
      setKind('reschedule')
      setNotice('Request sent for staff review. Your scheduled visit has not changed.')
    } catch (reason) {
      setActionError(reason instanceof TypeError ? 'Unable to reach the server. Try again.'
        : reason instanceof Error ? reason.message : 'Unable to submit the request.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="portal-card" aria-labelledby="portal-appointment-requests">
      <h2 id="portal-appointment-requests">Request an appointment change</h2>
      <p className="portal-help">
        Ask to cancel or reschedule a scheduled visit. Staff must review requests and
        make the scheduling change separately. Contact the clinic directly for urgent needs.
      </p>
      {!data && !error && <p role="status">Loading appointment requests...</p>}
      {error && <div>
        <p role="alert">{error}</p>
        <button type="button" className="secondary-action-button"
          onClick={() => setRefresh((value) => value + 1)}>Try Again</button>
      </div>}
      {data && <>
        {eligible.length === 0 ? (
          <p>No eligible appointments for a new request. An existing pending request
            also prevents another request for the same visit.</p>
        ) : (
          <form aria-labelledby="portal-appointment-requests" className="portal-change-form" data-unsaved={(appointmentId !== '' || kind !== 'reschedule') || undefined} onSubmit={(event) => void submit(event)}>
            <label htmlFor="request-appointment">Scheduled visit</label>
            <select id="request-appointment" value={appointmentId} disabled={saving} required
              onChange={(event) => { setAppointmentId(event.target.value); setActionError(null) }}>
              <option value="">Choose an appointment</option>
              {eligible.map((appointment) => <option key={appointment.id} value={appointment.id}>
                {formatPortalAppointment(appointment)}
                {' - '}{appointment.reason_for_visit}
              </option>)}
            </select>
            <label htmlFor="request-kind">Requested change</label>
            <select id="request-kind" value={kind} disabled={saving}
              onChange={(event) => setKind(event.target.value as 'cancel' | 'reschedule')}>
              <option value="reschedule">Reschedule</option>
              <option value="cancel">Cancel</option>
            </select>
            <button className="portal-primary-action" type="submit"
              disabled={!selected || saving}>{saving ? 'Sending...' : 'Send request'}</button>
          </form>
        )}
        {actionError && <p role="alert">{actionError}</p>}
        {notice && <p role="status" className="portal-confirmation">{notice}</p>}
        <div className="portal-change-history">
          <h3>My request history</h3>
          {data.requests.length === 0 ? <p>No requests submitted yet.</p> : (
            <ul className="portal-records">
              {data.requests.map((request) => <li key={request.id}>
                <strong>
                  {request.kind === 'cancel' ? 'Cancellation' : 'Rescheduling'} request
                  {' - '}{byId.get(request.appointment_id)?.reason_for_visit ??
                    'Appointment #' + request.appointment_id}
                </strong>
                <span>Sent <time dateTime={request.created_at}>
                  {new Date(request.created_at).toLocaleString()}
                </time></span>
                <span>{request.status === 'pending' ? 'Awaiting staff review'
                  : 'Reviewed by staff (change not confirmed)'}</span>
              </li>)}
            </ul>
          )}
        </div>
        <button type="button" className="secondary-action-button" disabled={saving}
          onClick={() => { setNotice(null); setRefresh((value) => value + 1) }}>
          Refresh requests
        </button>
      </>}
    </section>
  )
}
