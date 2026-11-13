import { useEffect, useRef, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Appointment, AppointmentStatus, PatientAppointment } from '../types'
import AppointmentForm from './AppointmentForm'
import AppointmentStatusHistory from './AppointmentStatusHistory'

type AppointmentListProps = {
  patientId: number
  highlightAppointmentId?: number | null
}

const statusLabels: Record<AppointmentStatus, string> = {
  scheduled: 'Scheduled',
  checked_in: 'Checked in',
  completed: 'Completed',
  cancelled: 'Cancelled',
  no_show: 'No-show',
}

function AppointmentList({
  patientId,
  highlightAppointmentId = null,
}: AppointmentListProps) {
  const [appointments, setAppointments] = useState<PatientAppointment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [editing, setEditing] = useState<Appointment | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)
  const [pendingAction, setPendingAction] = useState<{
    id: number
    action: 'check-in' | 'complete' | 'cancel' | 'no-show'
  } | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const reviewAppointmentRef = useRef<HTMLElement | null>(null)
  const focusedReviewId = useRef<number | null>(null)

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

        const records: PatientAppointment[] = await response.json()
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

  useEffect(() => {
    if (isLoading || error || highlightAppointmentId === null ||
        focusedReviewId.current === highlightAppointmentId) return

    if (!appointments.some((item) => item.id === highlightAppointmentId)) return

    const row = reviewAppointmentRef.current
    if (!row) return
    row.focus({ preventScroll: true })
    row.scrollIntoView({ behavior: 'smooth', block: 'center' })
    focusedReviewId.current = highlightAppointmentId
  }, [appointments, error, highlightAppointmentId, isLoading])

  function finishEditing() {
    setIsAdding(false)
    setEditing(null)
    setRefreshCount((count) => count + 1)
  }

  async function changeAppointmentStatus(
    appointment: Appointment,
    action: 'check-in' | 'complete' | 'cancel' | 'no-show'
  ) {
    setPendingAction({ id: appointment.id, action })
    setActionError(null)

    try {
      const response = await fetch(
        API_BASE_URL + '/appointments/' + appointment.id + '/' + action,
        { method: 'POST' }
      )

      if (!response.ok) {
        setActionError(await getApiErrorMessage(response))
        return
      }

      setRefreshCount((count) => count + 1)
    } catch (requestError) {
      console.error(requestError)
      setActionError(
        action === 'check-in'
          ? 'The appointment could not be checked in.'
          : action === 'complete'
            ? 'The appointment could not be completed.'
            : action === 'cancel'
              ? 'The appointment could not be cancelled.'
              : 'The appointment could not be marked as no-show.'
      )
    } finally {
      setPendingAction(null)
    }
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

      {actionError && (
        <p className="form-error" role="alert">{actionError}</p>
      )}

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
              <article
                className={appointment.id === highlightAppointmentId
                  ? 'appointment-row appointment-row-review'
                  : 'appointment-row'}
                key={appointment.id}
                ref={appointment.id === highlightAppointmentId ? reviewAppointmentRef : undefined}
                tabIndex={appointment.id === highlightAppointmentId ? -1 : undefined}
              >
                <div>
                  <strong>{appointment.reason_for_visit}</strong>
                  {appointment.id === highlightAppointmentId && (
                    <p className="appointment-review-note" role="status">
                      Appointment #{appointment.id} selected from the past appointments worklist.
                      Review the visit before changing its status.
                    </p>
                  )}
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
                  {appointment.visit_note_id !== null && (
                    <p className="appointment-meta">
                      Linked visit note #{appointment.visit_note_id}. Cancellation is unavailable
                      once a visit note is recorded.
                    </p>
                  )}
                  <AppointmentStatusHistory
                    appointmentId={appointment.id}
                    refreshCount={refreshCount}
                  />
                </div>

                <div className="appointment-actions">
                  {appointment.status === 'scheduled' && (
                    <button
                      className="secondary-action-button"
                      type="button"
                      disabled={pendingAction !== null}
                      aria-label={
                        'Check in appointment on ' + appointment.scheduled_date +
                        ' for ' + appointment.reason_for_visit
                      }
                      onClick={() =>
                        void changeAppointmentStatus(appointment, 'check-in')
                      }
                    >
                      {pendingAction?.id === appointment.id &&
                      pendingAction.action === 'check-in'
                        ? 'Checking in...'
                        : 'Check In'}
                    </button>
                  )}

                  {appointment.status === 'checked_in' && (
                    <button
                      className="secondary-action-button"
                      type="button"
                      disabled={pendingAction !== null}
                      aria-label={
                        'Complete appointment on ' + appointment.scheduled_date +
                        ' for ' + appointment.reason_for_visit
                      }
                      onClick={() =>
                        void changeAppointmentStatus(appointment, 'complete')
                      }
                    >
                      {pendingAction?.id === appointment.id &&
                      pendingAction.action === 'complete'
                        ? 'Completing...'
                        : 'Complete Appointment'}
                    </button>
                  )}

                  {appointment.status === 'scheduled' && (
                    <button
                      className="secondary-action-button"
                      type="button"
                      disabled={pendingAction !== null}
                      aria-label={
                        'Mark appointment on ' + appointment.scheduled_date +
                        ' for ' + appointment.reason_for_visit + ' as no-show'
                      }
                      onClick={() => {
                        const confirmed = window.confirm(
                          'Mark the appointment on ' +
                            appointment.scheduled_date +
                            ' at ' + appointment.start_time.slice(0, 5) +
                            ' for ' + appointment.reason_for_visit +
                            ' as no-show? This cannot be undone.'
                        )
                        if (confirmed) {
                          void changeAppointmentStatus(appointment, 'no-show')
                        }
                      }}
                    >
                      {pendingAction?.id === appointment.id &&
                      pendingAction.action === 'no-show'
                        ? 'Recording no-show...'
                        : 'No-show'}
                    </button>
                  )}

                  {(appointment.status === 'scheduled' ||
                    appointment.status === 'checked_in') &&
                    appointment.visit_note_id === null && (
                    <button
                      className="secondary-action-button appointment-cancel-button"
                      type="button"
                      disabled={pendingAction !== null}
                      aria-label={
                        'Cancel appointment on ' + appointment.scheduled_date +
                        ' for ' + appointment.reason_for_visit
                      }
                      onClick={() => {
                        const confirmed = window.confirm(
                          'Cancel the appointment on ' +
                            appointment.scheduled_date +
                            ' at ' + appointment.start_time.slice(0, 5) +
                            ' for ' + appointment.reason_for_visit +
                            '? This cannot be undone.'
                        )
                        if (confirmed) {
                          void changeAppointmentStatus(appointment, 'cancel')
                        }
                      }}
                    >
                      {pendingAction?.id === appointment.id &&
                      pendingAction.action === 'cancel'
                        ? 'Cancelling...'
                        : 'Cancel Appointment'}
                    </button>
                  )}

                  {appointment.status === 'scheduled' && (
                    <button
                      className="secondary-action-button"
                      type="button"
                      disabled={pendingAction !== null}
                      aria-label={
                        'Edit appointment on ' + appointment.scheduled_date +
                        ' for ' + appointment.reason_for_visit
                      }
                      onClick={() => setEditing(appointment)}
                    >
                      Edit
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
    </section>
  )
}

export default AppointmentList
