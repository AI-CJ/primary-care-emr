import { useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Appointment, AppointmentInput, AppointmentStatus } from '../types'

type AppointmentFormProps = {
  patientId: number
  appointment?: Appointment
  onSaved: () => void
  onCancel: () => void
}

const durations = [15, 30, 45, 60, 90, 120, 180]

function clinicToday(): string {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return year + '-' + month + '-' + day
}

function AppointmentForm({
  patientId,
  appointment,
  onSaved,
  onCancel,
}: AppointmentFormProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    const values = new FormData(event.currentTarget)

    const appointmentData: AppointmentInput = {
      scheduled_date: String(values.get('scheduled_date') ?? ''),
      start_time: String(values.get('start_time') ?? ''),
      duration_minutes: Number(values.get('duration_minutes')),
      reason_for_visit: String(values.get('reason_for_visit') ?? '').trim(),
      status: String(values.get('status') ?? 'scheduled') as AppointmentStatus,
    }

    const url = appointment
      ? API_BASE_URL + '/appointments/' + appointment.id
      : API_BASE_URL + '/patients/' + patientId + '/appointments'

    setIsSaving(true)

    try {
      const response = await fetch(url, {
        method: appointment ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(appointmentData),
      })

      if (!response.ok) {
        setError(await getApiErrorMessage(response))
        return
      }

      onSaved()
    } catch (requestError) {
      console.error(requestError)
      setError('The server could not be reached.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <form className="appointment-form" onSubmit={handleSubmit}>
      <p className="appointment-help">
        Development only. Use fictional patient information. Times are
        entered in the clinic's local time.
      </p>

      <div className="form-grid">
        <label className="form-field">
          <span>Appointment date *</span>
          <input
            name="scheduled_date"
            type="date"
            required
            defaultValue={appointment?.scheduled_date ?? clinicToday()}
          />
        </label>

        <label className="form-field">
          <span>Start time (clinic local) *</span>
          <input
            name="start_time"
            type="time"
            required
            defaultValue={appointment?.start_time.slice(0, 5) ?? '09:00'}
          />
        </label>

        <label className="form-field">
          <span>Duration *</span>
          <select
            name="duration_minutes"
            defaultValue={appointment?.duration_minutes ?? 30}
            required
          >
            {durations.map((minutes) => (
              <option value={minutes} key={minutes}>
                {minutes} minutes
              </option>
            ))}
          </select>
        </label>

        <label className="form-field">
          <span>Status *</span>
          <select
            name="status"
            defaultValue={appointment?.status ?? 'scheduled'}
            required
          >
            <option value="scheduled">Scheduled</option>
            <option value="checked_in">Checked in</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </label>
      </div>

      <label className="form-field">
        <span>Reason for visit *</span>
        <input
          name="reason_for_visit"
          type="text"
          required
          maxLength={200}
          defaultValue={appointment?.reason_for_visit ?? ''}
          placeholder="Annual wellness visit"
        />
      </label>

      {error && <p className="form-error" role="alert">{error}</p>}

      <div className="appointment-form-actions">
        <button
          className="save-patient-button"
          type="submit"
          disabled={isSaving}
        >
          {isSaving
            ? 'Saving...'
            : appointment
              ? 'Save Changes'
              : 'Schedule Appointment'}
        </button>
        <button
          className="secondary-action-button"
          type="button"
          onClick={onCancel}
          disabled={isSaving}
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

export default AppointmentForm
