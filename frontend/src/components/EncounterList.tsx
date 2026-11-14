import { useCallback, useEffect, useRef, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Encounter } from '../types'
import EncounterForm from './EncounterForm'
import EncounterAddenda from './EncounterAddenda'
import EncounterProblems from './EncounterProblems'
import EncounterVitals from './EncounterVitals'
import EncounterMedications from './EncounterMedications'
import EncounterAllergies from './EncounterAllergies'
import EncounterLabOrders from './EncounterLabOrders'
import EncounterReferrals from './EncounterReferrals'

type EncounterListProps = {
  patientId: number
  noteToReview?: { id: number; request: number } | null
  noteToStart?: { appointmentId: number; request: number } | null
  onNoteSaved?: () => void
}

const noteSections: Array<{
  key: 'subjective' | 'objective' | 'assessment' | 'plan' | 'patient_instructions'
  heading: string
}> = [
  { key: 'subjective', heading: 'Subjective' },
  { key: 'objective', heading: 'Objective' },
  { key: 'assessment', heading: 'Assessment' },
  { key: 'plan', heading: 'Plan' },
  { key: 'patient_instructions', heading: 'Patient instructions' },
]


function EncounterDetails({
  encounter,
  focusRequest,
}: {
  encounter: Encounter
  focusRequest: number | null
}) {
  const [isExpanded, setIsExpanded] = useState(false)
  const detailsRef = useRef<HTMLDetailsElement>(null)
  const summaryRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (focusRequest === null) return

    const details = detailsRef.current
    const summary = summaryRef.current
    if (!details || !summary) return

    details.open = true
    summary.focus({ preventScroll: true })
    details.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [focusRequest])

  return (
    <details
      ref={detailsRef}
      className="encounter-details"
      onToggle={(event) => setIsExpanded(event.currentTarget.open)}
    >
      <summary ref={summaryRef}>View note</summary>
      <div className="encounter-sections">
        {noteSections.map(({ key, heading }) =>
          encounter[key] && (
            <section className="encounter-section" key={key}>
              <h3>{heading}</h3>
              <p>{encounter[key]}</p>
            </section>
          )
        )}
        {isExpanded && <EncounterProblems encounter={encounter} />}
        {isExpanded && <EncounterVitals encounter={encounter} />}
        {isExpanded && <EncounterMedications encounter={encounter} />}
        {isExpanded && <EncounterAllergies encounter={encounter} />}
        {isExpanded && <EncounterLabOrders encounter={encounter} />}
        {isExpanded && <EncounterReferrals encounter={encounter} />}
        {encounter.finalized_at !== null && isExpanded && (
          <EncounterAddenda encounterId={encounter.id} />
        )}
      </div>
    </details>
  )
}

function EncounterList({
  patientId,
  noteToReview = null,
  noteToStart = null,
  onNoteSaved,
}: EncounterListProps) {
  const [encounters, setEncounters] = useState<Encounter[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [editing, setEditing] = useState<Encounter | null>(null)
  const [startingAppointmentId, setStartingAppointmentId] = useState<number | null>(null)
  const [startNoteMessage, setStartNoteMessage] = useState<string | null>(null)
  const handledStartRequest = useRef<number | null>(null)
  const startHeadingRef = useRef<HTMLHeadingElement>(null)
  const [finalizingId, setFinalizingId] = useState<number | null>(null)
  const [reviewedInstructionsId, setReviewedInstructionsId] = useState<number | null>(null)
  const [finalizeError, setFinalizeError] = useState<{
    encounterId: number
    message: string
  } | null>(null)

  const loadEncounters = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    setFinalizeError(null)
    setReviewedInstructionsId(null)
    setEncounters([])

    try {
      const response = await fetch(
        API_BASE_URL + '/patients/' + patientId + '/encounters'
      )
      if (!response.ok) {
        setError(await getApiErrorMessage(response))
        return
      }

      const data: Encounter[] = await response.json()
      setEncounters(data)
    } catch (requestError) {
      console.error(requestError)
      setError('Visit notes could not be loaded.')
    } finally {
      setIsLoading(false)
    }
  }, [patientId])

  useEffect(() => {
    void loadEncounters()
  }, [loadEncounters])

  useEffect(() => {
    if (!noteToStart || handledStartRequest.current === noteToStart.request) return

    handledStartRequest.current = noteToStart.request
    if (isAdding || editing) {
      setStartNoteMessage(
        'Close the current note form before starting a note for appointment #' +
        noteToStart.appointmentId + '.'
      )
      return
    }

    setStartNoteMessage(null)
    setStartingAppointmentId(noteToStart.appointmentId)
    setIsAdding(true)
  }, [noteToStart, isAdding, editing])

  useEffect(() => {
    if (!isAdding || startingAppointmentId === null) return
    startHeadingRef.current?.focus({ preventScroll: true })
    startHeadingRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [isAdding, startingAppointmentId])

  function closeAddForm() {
    setIsAdding(false)
    setStartingAppointmentId(null)
    setStartNoteMessage(null)
  }

  function finishEditing() {
    closeAddForm()
    setEditing(null)
    onNoteSaved?.()
    void loadEncounters()
  }

  async function handleFinalize(encounter: Encounter) {
    setFinalizeError(null)
    setFinalizingId(encounter.id)
    try {
      const response = await fetch(
        API_BASE_URL + '/encounters/' + encounter.id + '/finalize',
        { method: 'POST' }
      )
      if (!response.ok) {
        setFinalizeError({ encounterId: encounter.id, message: await getApiErrorMessage(response) })
        return
      }
      await loadEncounters()
    } catch (requestError) {
      console.error(requestError)
      setFinalizeError({ encounterId: encounter.id, message: 'The visit note could not be finalized.' })
    } finally {
      setFinalizingId(null)
    }
  }

  const linkedAppointmentIds = encounters.flatMap((encounter) =>
    encounter.appointment_id === null ? [] : [encounter.appointment_id]
  )

  return (
    <section className="overview-card encounter-card">
      <div className="overview-card-header">
        <h2>Visit Notes</h2>
        {!isAdding && !editing && (
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => {
              setStartingAppointmentId(null)
              setStartNoteMessage(null)
              setIsAdding(true)
            }}
          >
            + Add Visit Note
          </button>
        )}
      </div>

      {startNoteMessage && (
        <p className="form-error" role="status">{startNoteMessage}</p>
      )}

      {isAdding && (
        <div>
          {startingAppointmentId !== null && (
            <h3 ref={startHeadingRef} tabIndex={-1}>
              Visit note for appointment #{startingAppointmentId}
            </h3>
          )}
          <EncounterForm
            patientId={patientId}
            initialAppointmentId={startingAppointmentId}
            linkedAppointmentIds={linkedAppointmentIds}
            onSaved={finishEditing}
            onCancel={closeAddForm}
          />
        </div>
      )}

      {editing && (
        <EncounterForm
          patientId={patientId}
          encounter={editing}
          linkedAppointmentIds={linkedAppointmentIds}
          onSaved={finishEditing}
          onCancel={() => setEditing(null)}
        />
      )}

      {noteToReview && (isAdding || editing) && (
        <p role="status">
          Close the current note form to open linked visit note #{noteToReview.id}.
        </p>
      )}

      {!isAdding && !editing && isLoading && <p>Loading visit notes...</p>}

      {!isAdding && !editing && error && (
        <p className="form-error" role="alert">{error}</p>
      )}

      {!isLoading && !error && noteToReview &&
        !encounters.some((encounter) => encounter.id === noteToReview.id) && (
          <p className="form-error" role="alert">
            Linked visit note #{noteToReview.id} could not be found in this chart.
          </p>
        )}

      {!isAdding && !editing && !isLoading && !error &&
        encounters.length === 0 && <p>No visit notes recorded yet.</p>}

      {!isAdding && !editing && !isLoading && !error &&
        encounters.length > 0 && (
          <div className="encounter-list">
            {encounters.map((encounter) => (
              <article
                className={encounter.id === noteToReview?.id
                  ? 'encounter-row encounter-row-review'
                  : 'encounter-row'}
                key={encounter.id}
              >
                <div className="encounter-row-header">
                  <div>
                    <strong>{encounter.reason_for_visit}</strong>
                    <p className="encounter-meta">
                      Visit date: <time dateTime={encounter.visit_date}>
                        {encounter.visit_date}
                      </time>
                      {encounter.appointment_id !== null && (
                        <span> · Linked appointment #{encounter.appointment_id}</span>
                      )}
                      {encounter.finalized_at !== null && (
                        <span> · Finalized <time dateTime={encounter.finalized_at}>{encounter.finalized_at.slice(0, 10)}</time></span>
                      )}
                    </p>
                  </div>
                  {encounter.finalized_at === null && (
                    <button
                      className="secondary-action-button"
                      type="button"
                      aria-label={
                        'Edit visit note from ' + encounter.visit_date +
                        ': ' + encounter.reason_for_visit
                      }
                      disabled={finalizingId !== null}
                      onClick={() => setEditing(encounter)}
                    >
                      Edit
                    </button>
                  )}
                </div>

                <EncounterDetails
                  encounter={encounter}
                  focusRequest={
                    encounter.id === noteToReview?.id ? noteToReview.request : null
                  }
                />
                {encounter.finalized_at === null && (
                  <details className="encounter-finalize-review">
                    <summary>Review and finalize</summary>
                    <div className="encounter-finalize-content">
                      <p>
                        Finalizing locks this note. The visit date, reason, and any patient
                        instructions below will appear in the patient portal preview.
                        Check for information that should stay in the staff chart.
                      </p>
                      <h3>Patient instructions to release</h3>
                      {encounter.patient_instructions ? (
                        <p className="encounter-release-text">{encounter.patient_instructions}</p>
                      ) : (
                        <p>No patient instructions entered for this visit.</p>
                      )}
                      {encounter.patient_instructions && (
                        <label className="encounter-release-confirmation">
                          <input
                            type="checkbox"
                            checked={reviewedInstructionsId === encounter.id}
                            disabled={finalizingId !== null}
                            onChange={(event) => setReviewedInstructionsId(
                              event.target.checked ? encounter.id : null
                            )}
                          />
                          <span>
                            I reviewed these instructions and confirmed they are appropriate
                            for the patient portal preview.
                          </span>
                        </label>
                      )}
                      {(!encounter.assessment || !encounter.plan) && (
                        <p>Complete the assessment and plan before finalizing this note.</p>
                      )}
                      {finalizeError?.encounterId === encounter.id && (
                        <p className="form-error" role="alert">{finalizeError.message}</p>
                      )}
                      <div className="encounter-form-actions">
                        <button
                          className="save-patient-button"
                          type="button"
                          disabled={
                            finalizingId !== null || !encounter.assessment || !encounter.plan ||
                            (Boolean(encounter.patient_instructions) &&
                              reviewedInstructionsId !== encounter.id)
                          }
                          onClick={() => void handleFinalize(encounter)}
                        >
                          {finalizingId === encounter.id ? 'Finalizing...' : 'Confirm finalization'}
                        </button>
                      </div>
                    </div>
                  </details>
                )}
              </article>
            ))}
          </div>
        )}
    </section>
  )
}

export default EncounterList
