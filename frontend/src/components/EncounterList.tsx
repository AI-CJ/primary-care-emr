import { useCallback, useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Encounter } from '../types'
import EncounterForm from './EncounterForm'
import EncounterAddenda from './EncounterAddenda'
import EncounterProblems from './EncounterProblems'
import EncounterVitals from './EncounterVitals'
import EncounterMedications from './EncounterMedications'
import EncounterAllergies from './EncounterAllergies'

type EncounterListProps = {
  patientId: number
}

const noteSections: Array<{
  key: 'subjective' | 'objective' | 'assessment' | 'plan'
  heading: string
}> = [
  { key: 'subjective', heading: 'Subjective' },
  { key: 'objective', heading: 'Objective' },
  { key: 'assessment', heading: 'Assessment' },
  { key: 'plan', heading: 'Plan' },
]


function EncounterDetails({ encounter }: { encounter: Encounter }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <details
      className="encounter-details"
      onToggle={(event) => setIsExpanded(event.currentTarget.open)}
    >
      <summary>View note</summary>
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
        {encounter.finalized_at !== null && isExpanded && (
          <EncounterAddenda encounterId={encounter.id} />
        )}
      </div>
    </details>
  )
}

function EncounterList({ patientId }: EncounterListProps) {
  const [encounters, setEncounters] = useState<Encounter[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [editing, setEditing] = useState<Encounter | null>(null)
  const [finalizingId, setFinalizingId] = useState<number | null>(null)
  const [finalizeError, setFinalizeError] = useState<string | null>(null)

  const loadEncounters = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    setFinalizeError(null)
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

  function finishEditing() {
    setIsAdding(false)
    setEditing(null)
    void loadEncounters()
  }

  async function handleFinalize(encounter: Encounter) {
    if (!window.confirm('Finalize this visit note? It cannot be edited afterward.')) {
      return
    }

    setFinalizeError(null)
    setFinalizingId(encounter.id)
    try {
      const response = await fetch(
        API_BASE_URL + '/encounters/' + encounter.id + '/finalize',
        { method: 'POST' }
      )
      if (!response.ok) {
        setFinalizeError(await getApiErrorMessage(response))
        return
      }
      await loadEncounters()
    } catch (requestError) {
      console.error(requestError)
      setFinalizeError('The visit note could not be finalized.')
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
            onClick={() => setIsAdding(true)}
          >
            + Add Visit Note
          </button>
        )}
      </div>

      {isAdding && (
        <EncounterForm
          patientId={patientId}
          linkedAppointmentIds={linkedAppointmentIds}
          onSaved={finishEditing}
          onCancel={() => setIsAdding(false)}
        />
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

      {!isAdding && !editing && isLoading && <p>Loading visit notes...</p>}

      {!isAdding && !editing && error && (
        <p className="form-error" role="alert">{error}</p>
      )}

      {!isAdding && !editing && finalizeError && (
        <p className="form-error" role="alert">{finalizeError}</p>
      )}

      {!isAdding && !editing && !isLoading && !error &&
        encounters.length === 0 && <p>No visit notes recorded yet.</p>}

      {!isAdding && !editing && !isLoading && !error &&
        encounters.length > 0 && (
          <div className="encounter-list">
            {encounters.map((encounter) => (
              <article className="encounter-row" key={encounter.id}>
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
                    <div className="encounter-form-actions">
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
                      <button
                        className="secondary-action-button"
                        type="button"
                        aria-label={'Finalize visit note from ' + encounter.visit_date}
                        disabled={finalizingId !== null}
                        onClick={() => void handleFinalize(encounter)}
                      >
                        {finalizingId === encounter.id ? 'Finalizing...' : 'Finalize'}
                      </button>
                    </div>
                  )}
                </div>

                <EncounterDetails encounter={encounter} />
              </article>
            ))}
          </div>
        )}
    </section>
  )
}

export default EncounterList
