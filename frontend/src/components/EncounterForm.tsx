import { useEffect, useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Encounter, EncounterInput, PatientAppointment } from '../types'

type EncounterFormProps = {
  patientId: number
  encounter?: Encounter
  linkedAppointmentIds: number[]
  initialAppointmentId?: number | null
  onSaved: () => void
  onCancel: () => void
}

function EncounterForm({
  patientId,
  encounter,
  linkedAppointmentIds,
  initialAppointmentId = null,
  onSaved,
  onCancel,
}: EncounterFormProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [visitDate, setVisitDate] = useState(encounter?.visit_date ?? '')
  const [reasonForVisit, setReasonForVisit] = useState(
    encounter?.reason_for_visit ?? ''
  )
  const [selectedAppointmentId, setSelectedAppointmentId] = useState(
    initialAppointmentId === null ? '' : String(initialAppointmentId)
  )
  const [appointments, setAppointments] = useState<PatientAppointment[]>([])
  const [isLoadingAppointments, setIsLoadingAppointments] = useState(!encounter)
  const [appointmentError, setAppointmentError] = useState<string | null>(null)

  useEffect(() => {
    if (encounter) return

    const controller = new AbortController()

    async function loadAppointments() {
      try {
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/appointments',
          { signal: controller.signal }
        )
        if (!response.ok) {
          const message = await getApiErrorMessage(response)
          if (!controller.signal.aborted) setAppointmentError(message)
          return
        }

        const records: PatientAppointment[] = await response.json()
        if (!controller.signal.aborted) {
          setAppointments(records)
          if (initialAppointmentId !== null) {
            const appointment = records.find((item) =>
              item.id === initialAppointmentId &&
              (item.status === 'checked_in' || item.status === 'completed') &&
              item.visit_note_id === null
            )
            if (appointment) {
              setVisitDate(appointment.scheduled_date)
              setReasonForVisit(appointment.reason_for_visit)
            } else {
              setError('This appointment can no longer be linked to a new visit note.')
            }
          }
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setAppointmentError('Appointments could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoadingAppointments(false)
      }
    }

    void loadAppointments()
    return () => controller.abort()
  }, [patientId, encounter, initialAppointmentId])

  const availableAppointments = appointments.filter(
    (appointment) =>
      (appointment.status === 'checked_in' || appointment.status === 'completed') &&
      appointment.visit_note_id === null &&
      !linkedAppointmentIds.includes(appointment.id)
  )

  function chooseAppointment(id: string) {
    setError(null)
    setSelectedAppointmentId(id)
    const selected = availableAppointments.find(
      (appointment) => String(appointment.id) === id
    )
    if (selected) {
      setVisitDate(selected.scheduled_date)
      setReasonForVisit(selected.reason_for_visit)
    }
  }

  function optionalText(formData: FormData, name: string): string | null {
    const value = String(formData.get(name) ?? '').trim()
    return value || null
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    const appointmentId = selectedAppointmentId
      ? Number(selectedAppointmentId)
      : null
    if (
      appointmentId !== null &&
      !availableAppointments.some((appointment) => appointment.id === appointmentId)
    ) {
      setError('The selected appointment is no longer available.')
      return
    }

    const formData = new FormData(event.currentTarget)
    const encounterData: EncounterInput = {
      visit_date: visitDate,
      reason_for_visit: reasonForVisit.trim(),
      subjective: optionalText(formData, 'subjective'),
      objective: optionalText(formData, 'objective'),
      assessment: optionalText(formData, 'assessment'),
      plan: optionalText(formData, 'plan'),
      patient_instructions: optionalText(formData, 'patient_instructions'),
      ...(!encounter && appointmentId !== null
        ? { appointment_id: appointmentId }
        : {}),
    }

    if (
      !encounterData.subjective &&
      !encounterData.objective &&
      !encounterData.assessment &&
      !encounterData.plan
    ) {
      setError('Complete at least one visit note section.')
      return
    }

    setIsSaving(true)
    const url = encounter
      ? API_BASE_URL + '/encounters/' + encounter.id
      : API_BASE_URL + '/patients/' + patientId + '/encounters'

    try {
      const response = await fetch(url, {
        method: encounter ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(encounterData),
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
    <form className="encounter-form" onSubmit={handleSubmit}>
      <p className="encounter-help">
        Development only: enter fictional patient information, never real records.
      </p>

      {!encounter && (
        <>
          <label className="form-field">
            <span>Linked appointment (optional)</span>
            <select
              value={selectedAppointmentId}
              onChange={(event) => chooseAppointment(event.target.value)}
              disabled={isLoadingAppointments || appointmentError !== null}
            >
              <option value="">Standalone visit note</option>
              {initialAppointmentId !== null &&
                !availableAppointments.some((item) => item.id === initialAppointmentId) && (
                <option value={initialAppointmentId}>
                  Appointment #{initialAppointmentId} (
                  {isLoadingAppointments ? 'loading' : 'unavailable'})
                </option>
              )}
              {availableAppointments.map((appointment) => (
                <option key={appointment.id} value={appointment.id}>
                  {appointment.scheduled_date} at {appointment.start_time.slice(0, 5)}
                  {' · '}{appointment.reason_for_visit}
                  {' ('}{appointment.status === 'checked_in' ? 'Checked in' : 'Completed'}{')'}
                </option>
              ))}
            </select>
          </label>
          {isLoadingAppointments && (
            <p className="encounter-help" role="status">Loading appointments...</p>
          )}
          {appointmentError && (
            <p className="form-error" role="alert">
              {appointmentError} {initialAppointmentId === null
                ? 'You can still save a standalone note.'
                : 'Close this form and try again from the appointment list.'}
            </p>
          )}
          {!isLoadingAppointments && !appointmentError && (
            <p className="encounter-help">
              Only checked-in or completed appointments without a visit note can be linked.
            </p>
          )}
        </>
      )}

      {encounter?.appointment_id != null && (
        <p className="encounter-help">
          Linked to appointment #{encounter.appointment_id}. The link cannot be changed.
        </p>
      )}

      <label className="form-field">
        <span>Visit date *</span>
        <input
          type="date"
          name="visit_date"
          required
          value={visitDate}
          onChange={(event) => setVisitDate(event.target.value)}
          readOnly={selectedAppointmentId !== '' || encounter?.appointment_id != null}
        />
      </label>

      <label className="form-field">
        <span>Reason for visit *</span>
        <input
          type="text"
          name="reason_for_visit"
          required
          maxLength={200}
          value={reasonForVisit}
          onChange={(event) => setReasonForVisit(event.target.value)}
        />
      </label>

      <p className="encounter-help">Complete at least one note section.</p>

      <label className="form-field">
        <span>Subjective</span>
        <textarea
          name="subjective"
          rows={4}
          maxLength={4000}
          defaultValue={encounter?.subjective ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Objective</span>
        <textarea
          name="objective"
          rows={4}
          maxLength={4000}
          defaultValue={encounter?.objective ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Assessment</span>
        <textarea
          name="assessment"
          rows={4}
          maxLength={4000}
          defaultValue={encounter?.assessment ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Plan</span>
        <textarea
          name="plan"
          rows={4}
          maxLength={4000}
          defaultValue={encounter?.plan ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Instructions for patient (optional)</span>
        <textarea
          name="patient_instructions"
          rows={4}
          maxLength={4000}
          defaultValue={encounter?.patient_instructions ?? ''}
        />
      </label>
      <p className="encounter-help">
        After finalization, the visit date, reason, and these instructions appear in the
        patient portal preview. Do not copy private clinical notes into patient instructions.
      </p>

      {error && <p className="form-error" role="alert">{error}</p>}

      <div className="encounter-form-actions">
        <button
          className="save-patient-button"
          type="submit"
          disabled={isSaving}
        >
          {isSaving ? 'Saving...' : encounter ? 'Save Changes' : 'Save Visit Note'}
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

export default EncounterForm
