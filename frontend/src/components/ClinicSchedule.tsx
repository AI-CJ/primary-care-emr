import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { AppointmentStatus, ScheduleEntry } from '../types'

type ClinicScheduleProps = {
  day: string
  onDayChange: (day: string) => void
  onBack: () => void
  onOpenPatient: (patientId: number, appointmentId: number) => void
  patientError: string | null
}

const statusLabels: Record<AppointmentStatus, string> = {
  scheduled: 'Scheduled',
  checked_in: 'Checked in',
  completed: 'Completed',
  cancelled: 'Cancelled',
  no_show: 'No-show',
}

export function localDate(): string {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function moveDate(day: string, offset: number): string {
  const [year, month, date] = day.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, date + offset))
    .toISOString()
    .slice(0, 10)
}

function formatTime(value: string): string {
  const [hourText, minute] = value.split(':')
  const hour = Number(hourText)
  const hour12 = hour % 12 || 12
  return `${hour12}:${minute} ${hour >= 12 ? 'PM' : 'AM'}`
}

function ClinicSchedule({
  day,
  onDayChange,
  onBack,
  onOpenPatient,
  patientError,
}: ClinicScheduleProps) {
  const [result, setResult] = useState<{
    day: string
    entries: ScheduleEntry[]
  } | null>(null)
  const [failure, setFailure] = useState<{
    day: string
    message: string
  } | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadSchedule() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/schedule?day=${encodeURIComponent(day)}`,
          { signal: controller.signal },
        )

        if (!response.ok) {
          throw new Error(await getApiErrorMessage(response))
        }

        const entries: ScheduleEntry[] = await response.json()
        if (!controller.signal.aborted) {
          setResult({ day, entries })
          setFailure(null)
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setResult(null)
          setFailure({
            day,
            message: requestError instanceof TypeError
              ? 'The server could not be reached. Try again.'
              : requestError instanceof Error
                ? requestError.message
                : 'The schedule could not be loaded.',
          })
        }
      }
    }

    void loadSchedule()
    return () => controller.abort()
  }, [day])

  const entries = result?.day === day ? result.entries : null
  const error = failure?.day === day ? failure.message : null

  return (
    <main className="search-page">
      <section className="search-panel schedule-panel">
        <button className="back-button" type="button" onClick={onBack}>
          ← Back to patient search
        </button>

        <header className="schedule-header">
          <div>
            <h1>Clinic Schedule</h1>
            <p>Appointments for the selected day. Open a patient chart to make changes.</p>
          </div>
        </header>

        <div className="schedule-controls">
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => onDayChange(moveDate(day, -1))}
          >
            ← Previous day
          </button>
          <label className="schedule-date-field" htmlFor="schedule-day">
            <span>Schedule date</span>
            <input
              id="schedule-day"
              type="date"
              value={day}
              onChange={(event) => {
                if (event.target.value) onDayChange(event.target.value)
              }}
            />
          </label>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => onDayChange(localDate())}
          >
            Today
          </button>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => onDayChange(moveDate(day, 1))}
          >
            Next day →
          </button>
        </div>

        {patientError && <p className="form-error" role="alert">{patientError}</p>}

        {!entries && !error && (
          <p className="empty-message" role="status">Loading schedule...</p>
        )}
        {error && <p className="form-error" role="alert">{error}</p>}
        {entries && entries.length === 0 && (
          <p className="empty-message">No appointments for this date.</p>
        )}

        {entries && entries.length > 0 && (
          <>
            <p className="schedule-count" role="status">
              {entries.length} appointment{entries.length === 1 ? '' : 's'}
            </p>
            <ol className="clinic-schedule-list">
              {entries.map(({ appointment, patient }) => (
                <li className="clinic-schedule-row" key={appointment.id}>
                  <div className="schedule-time">
                    <time dateTime={`${appointment.scheduled_date}T${appointment.start_time}`}>
                      {formatTime(appointment.start_time)}
                    </time>
                    <span>{appointment.duration_minutes} min</span>
                  </div>
                  <div className="schedule-entry-detail">
                    <button
                      type="button"
                      className="schedule-patient-link"
                      onClick={() => onOpenPatient(patient.id, appointment.id)}
                    >
                      {patient.preferred_name || patient.first_name} {patient.last_name}
                    </button>
                    <p>{appointment.reason_for_visit}</p>
                    <span className="schedule-dob">DOB {patient.date_of_birth}</span>
                  </div>
                  <span className={`appointment-status appointment-status-${appointment.status}`}>
                    {statusLabels[appointment.status]}
                  </span>
                </li>
              ))}
            </ol>
          </>
        )}
      </section>
    </main>
  )
}

export default ClinicSchedule
