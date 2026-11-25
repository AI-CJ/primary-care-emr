import { useEffect, useState } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type { PortalAppointmentSummary } from '../types'
import { localDate } from '../date'
import { groupPortalAppointments, formatPortalAppointment } from '../portalAppointments'

type PortalAppointmentsProps = {
  patientId?: number
}

function PortalAppointments({ patientId }: PortalAppointmentsProps) {
  const [appointments, setAppointments] = useState<PortalAppointmentSummary[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadAppointments() {
      setIsLoading(true)
      setError(null)
      setAppointments(null)

      try {
        const response = await apiFetch(
          patientId === undefined
            ? `${API_BASE_URL}/portal/appointments`
            : `${API_BASE_URL}/patients/${patientId}/portal-preview/appointments`,
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: PortalAppointmentSummary[] = await response.json()
        if (!controller.signal.aborted) setAppointments(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof TypeError
            ? 'Appointments could not be loaded. Check your connection and try again.'
            : requestError instanceof Error
              ? requestError.message
              : 'Appointments could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadAppointments()
    return () => controller.abort()
  }, [patientId, refreshCount])

  const { upcoming, earlierOpen, history } = groupPortalAppointments(appointments ?? [], localDate())

  return (
    <section className="portal-card" aria-labelledby="portal-appointments">
      <h2 id="portal-appointments">My appointments</h2>
      <p className="portal-help">Upcoming visits and appointment history. A request to change a visit does not change the scheduled appointment until the clinic acts.</p>

      {isLoading && <p role="status">Loading appointments...</p>}
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
      {!isLoading && !error && upcoming.length === 0 && (
        <p>No upcoming appointments are listed in your chart.</p>
      )}
      {!isLoading && !error && upcoming.length > 0 && (
        <ul className="portal-records">
          {upcoming.map((appointment) => (
            <li key={appointment.id}>
              <strong>{appointment.reason_for_visit}</strong>
              <time dateTime={`${appointment.scheduled_date}T${appointment.start_time}`}>
                {formatPortalAppointment(appointment)}
              </time>
              <span className="portal-record-status">{appointment.status === 'checked_in' ? 'Checked in' : 'Scheduled'}</span>
            </li>
          ))}
        </ul>
      )}
      {!isLoading && !error && earlierOpen.length > 0 && (
        <div className="portal-lab-group">
          <h3>Earlier appointments still marked open</h3>
          <p className="portal-help">The clinic has not recorded a final status for these visits.</p>
          <ul className="portal-records">{earlierOpen.map(appointment => <li key={appointment.id}>
            <strong>{appointment.reason_for_visit}</strong>
            <time dateTime={`${appointment.scheduled_date}T${appointment.start_time}`}>{formatPortalAppointment(appointment)}</time>
            <span className="portal-record-status">{appointment.status === 'checked_in' ? 'Checked in' : 'Scheduled'}</span>
          </li>)}</ul>
        </div>
      )}
      {!isLoading && !error && history.length > 0 && (
        <details>
          <summary>Appointment history ({history.length})</summary>
          <ul className="portal-records">
            {history.map((appointment) => (
              <li key={appointment.id}>
                <strong>{appointment.reason_for_visit}</strong>
                <time dateTime={`${appointment.scheduled_date}T${appointment.start_time}`}>
                  {formatPortalAppointment(appointment)}
                </time>
                <span>
                  Recorded status: {appointment.status === 'no_show'
                    ? 'No-show' : appointment.status === 'cancelled'
                      ? 'Cancelled' : 'Completed'}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}

export default PortalAppointments
