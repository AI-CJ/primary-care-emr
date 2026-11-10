import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Appointment } from '../types'

type PortalAppointmentsProps = {
  patientId: number
}

function localToday(): string {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatTime(value: string): string {
  const [hours, minutes] = value.split(':')
  const hour = Number(hours)
  return `${hour % 12 || 12}:${minutes} ${hour >= 12 ? 'PM' : 'AM'}`
}

function PortalAppointments({ patientId }: PortalAppointmentsProps) {
  const [appointments, setAppointments] = useState<Appointment[] | null>(null)
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
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/appointments',
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: Appointment[] = await response.json()
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

  const today = localToday()
  const upcoming = (appointments ?? [])
    .filter((appointment) =>
      (appointment.status === 'scheduled' || appointment.status === 'checked_in') &&
      appointment.scheduled_date >= today
    )
    .sort((first, second) =>
      first.scheduled_date.localeCompare(second.scheduled_date) ||
      first.start_time.localeCompare(second.start_time) ||
      first.id - second.id
    )

  const history = (appointments ?? [])
    .filter((appointment) =>
      appointment.status === 'completed' ||
      appointment.status === 'cancelled' ||
      appointment.status === 'no_show'
    )
    .sort((first, second) =>
      second.scheduled_date.localeCompare(first.scheduled_date) ||
      second.start_time.localeCompare(first.start_time) ||
      second.id - first.id
    )
    .slice(0, 5)

  return (
    <section className="portal-card" aria-labelledby="portal-appointments">
      <h2 id="portal-appointments">My appointments</h2>
      <p className="portal-help">Upcoming visits and recent appointment history. Contact the clinic to make changes.</p>

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
                {appointment.scheduled_date} at {formatTime(appointment.start_time)}
              </time>
              {appointment.status === 'checked_in' && <span>Checked in</span>}
            </li>
          ))}
        </ul>
      )}
      {!isLoading && !error && history.length > 0 && (
        <details>
          <summary>Recent appointment history ({history.length})</summary>
          <ul className="portal-records">
            {history.map((appointment) => (
              <li key={appointment.id}>
                <strong>{appointment.reason_for_visit}</strong>
                <time dateTime={`${appointment.scheduled_date}T${appointment.start_time}`}>
                  {appointment.scheduled_date} at {formatTime(appointment.start_time)}
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
