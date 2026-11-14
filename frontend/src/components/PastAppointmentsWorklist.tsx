import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import { localDate } from './ClinicSchedule'
import type { ScheduleEntry } from '../types'

type PastAppointmentsWorklistProps = {
  onBack: () => void
  onOpenPatient: (patientId: number, appointmentId: number) => void
  patientError: string | null
}

function formatTime(value: string): string {
  const [hours, minutes] = value.split(':')
  const hour = Number(hours)
  return `${hour % 12 || 12}:${minutes} ${hour >= 12 ? 'PM' : 'AM'}`
}

function PastAppointmentsWorklist({
  onBack,
  onOpenPatient,
  patientError,
}: PastAppointmentsWorklistProps) {
  const [appointments, setAppointments] = useState<ScheduleEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)
  const [pendingNoShowId, setPendingNoShowId] = useState<number | null>(null)
  const [statusError, setStatusError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setAppointments(null)
    setError(null)
    setStatusError(null)

    async function loadAppointments() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/worklists/past-appointments?before=${localDate()}`,
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: ScheduleEntry[] = await response.json()
        if (!controller.signal.aborted) setAppointments(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof TypeError
            ? 'The server could not be reached. Try again.'
            : requestError instanceof Error
              ? requestError.message
              : 'Past appointments could not be loaded.')
        }
      }
    }

    void loadAppointments()
    return () => controller.abort()
  }, [refreshCount])

  async function markNoShow(
    appointment: ScheduleEntry['appointment'],
    patient: ScheduleEntry['patient'],
  ) {
    const patientName = `${patient.preferred_name || patient.first_name} ${patient.last_name}`
    const confirmed = window.confirm(
      `Mark the appointment for ${patientName} on ${appointment.scheduled_date} ` +
      `at ${formatTime(appointment.start_time)} as no-show?\n\n` +
      'Confirm the patient did not attend before making this permanent change.'
    )
    if (!confirmed) return

    setPendingNoShowId(appointment.id)
    setStatusError(null)
    try {
      const response = await fetch(
        `${API_BASE_URL}/appointments/${appointment.id}/no-show`,
        { method: 'POST' },
      )
      if (!response.ok) {
        setStatusError(await getApiErrorMessage(response))
        return
      }
      setRefreshCount((count) => count + 1)
    } catch (requestError) {
      console.error(requestError)
      setStatusError('The appointment could not be marked as no-show.')
    } finally {
      setPendingNoShowId(null)
    }
  }

  return (
    <main className="search-page">
      <section className="search-panel schedule-panel" aria-labelledby="past-appointments-heading">
        <button className="back-button" type="button" onClick={onBack}>
          ← Back to patient search
        </button>
        <div className="search-panel-header">
          <div>
            <h1 id="past-appointments-heading">Past Appointments to Review</h1>
            <p className="pending-lab-intro">
              Appointments from previous days still marked scheduled or checked in.
              Review the patient chart before changing a status. Scheduled appointments
              can be marked no-show here after confirming the patient did not attend.
            </p>
          </div>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setRefreshCount((count) => count + 1)}
            disabled={(appointments === null && error === null) || pendingNoShowId !== null}
          >
            Refresh
          </button>
        </div>

        {patientError && <p className="form-error" role="alert">{patientError}</p>}
        {statusError && <p className="form-error" role="alert">{statusError}</p>}
        {!appointments && !error && (
          <p className="empty-message" role="status">Loading past appointments...</p>
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
        {appointments && (
          <>
            <p className="schedule-count" role="status">
              {appointments.length} appointment{appointments.length === 1 ? '' : 's'} to review
            </p>
            {appointments.length === 0 ? (
              <p className="empty-message">No past appointments need status review.</p>
            ) : (
              <ol className="pending-lab-list">
                {appointments.map(({ appointment, patient }) => (
                  <li className="pending-lab-row" key={appointment.id}>
                    <div>
                      <div className="pending-lab-title">
                        <strong>{appointment.reason_for_visit}</strong>
                        <span className="pending-lab-priority">
                          {appointment.status === 'checked_in' ? 'Checked in' : 'Scheduled'}
                        </span>
                      </div>
                      <p className="pending-lab-meta">
                        <time dateTime={`${appointment.scheduled_date}T${appointment.start_time}`}>
                          {appointment.scheduled_date} at {formatTime(appointment.start_time)}
                        </time>
                        {' · '}Appointment #{appointment.id}
                      </p>
                    </div>
                    <div className="pending-lab-patient">
                      <button
                        className="schedule-patient-link"
                        type="button"
                        onClick={() => onOpenPatient(patient.id, appointment.id)}
                        aria-label={`Review appointment #${appointment.id} for ${patient.preferred_name || patient.first_name} ${patient.last_name}`}
                      >
                        {patient.preferred_name || patient.first_name} {patient.last_name}
                      </button>
                      <span>Review this appointment in the patient chart</span>
                      {appointment.status === 'scheduled' && (
                        <button
                          className="secondary-action-button"
                          type="button"
                          disabled={pendingNoShowId !== null}
                          aria-label={`Mark appointment #${appointment.id} for ${patient.preferred_name || patient.first_name} ${patient.last_name} as no-show`}
                          onClick={() => void markNoShow(appointment, patient)}
                        >
                          {pendingNoShowId === appointment.id ? 'Recording no-show...' : 'Mark No-show'}
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
        <p className="pending-lab-disclaimer">
          Synthetic-data demonstration. No-show updates require staff confirmation and are recorded in appointment status history.
        </p>
      </section>
    </main>
  )
}

export default PastAppointmentsWorklist
