import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Appointment, AppointmentStatus } from '../types'
import AppointmentForm from './AppointmentForm'

type AppointmentListProps = {
  patientId: number
}

const statusLabels: Record<AppointmentStatus, string> = {
  scheduled: 'Scheduled',
  checked_in: 'Checked in',
  completed: 'Completed',
  cancelled: 'Cancelled',
}

function AppointmentList({ patientId }: AppointmentListProps) {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [editing, setEditing] = useState<Appointment | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadAppointments() {
      setIsLoading(true)
      setError(null)
      setAppointments([])

      try {
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/appointments',
          { signal: controller.signal }
        )

        if (!response.ok) {
          const message = await getApiErrorMessage(response)
          if (!controller.signal.aborted) setError(message)
          return
        }

        const records: Appointment[] = await response.json()
        if (!controller.signal.aborted) setAppointments(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setError('Appointments could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadAppointments()
    return () => controller.abort()
  }, [patientId, refreshCount])

  function finishEditing() {
    setIsAdding(false)
    setEditing(null)
    setRefreshCount((count) => count + 1)
  }

  return (
    <section className="overview-card appointment-card">
      <div className="overview-card-header">
        <h2>Appointments</h2>
        {!isAdding && !editing && (
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setIsAdding(true)}
          >
            + Schedule Appointment
          </button>
        )}
      </div>

      {isAdding && (
        <AppointmentForm
          patientId={patientId}
          onSaved={finishEditing}
          onCancel={() => setIsAdding(false)}
        />
      )}

      {editing && (
        <AppointmentForm
          patientId={patientId}
          appointment={editing}
          onSaved={finishEditing}
          onCancel={() => setEditing(null)}
        />
      )}

      {!isAdding && !editing && isLoading && (
        <p role="status">Loading appointments...</p>
      )}

      {!isAdding && !editing && error && (
        <p className="form-error" role="alert">{error}</p>
      )}

      {!isAdding && !editing && !isLoading && !error &&
        appointments.length === 0 && <p>No appointments scheduled yet.</p>}

      {!isAdding && !editing && !isLoading && !error &&
        appointments.length > 0 && (
          <div className="appointment-list">
            {appointments.map((appointment) => (
              <article className="appointment-row" key={appointment.id}>
                <div>
                  <strong>{appointment.reason_for_visit}</strong>
                  <p className="appointment-meta">
                    <time dateTime={appointment.scheduled_date}>
                      {appointment.scheduled_date}
                    </time>
                    {' at '}
                    {appointment.start_time.slice(0, 5)}
                    {' · '}
                    {appointment.duration_minutes} min
                    {' · '}
                    <span className={
                      'appointment-status appointment-status-' +
                      appointment.status
                    }>
                      {statusLabels[appointment.status]}
                    </span>
                  </p>
                </div>

                <button
                  className="secondary-action-button"
                  type="button"
                  aria-label={
                    'Edit appointment on ' + appointment.scheduled_date +
                    ' for ' + appointment.reason_for_visit
                  }
                  onClick={() => setEditing(appointment)}
                >
                  Edit
                </button>
              </article>
            ))}
          </div>
        )}
    </section>
  )
}

export default AppointmentList
