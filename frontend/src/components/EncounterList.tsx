import { useCallback, useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Encounter } from '../types'
import EncounterForm from './EncounterForm'

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

function EncounterList({ patientId }: EncounterListProps) {
  const [encounters, setEncounters] = useState<Encounter[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [editing, setEditing] = useState<Encounter | null>(null)

  const loadEncounters = useCallback(async () => {
    setIsLoading(true)
    setError(null)
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
          onSaved={finishEditing}
          onCancel={() => setIsAdding(false)}
        />
      )}

      {editing && (
        <EncounterForm
          patientId={patientId}
          encounter={editing}
          onSaved={finishEditing}
          onCancel={() => setEditing(null)}
        />
      )}

      {!isAdding && !editing && isLoading && <p>Loading visit notes...</p>}

      {!isAdding && !editing && error && (
        <p className="form-error" role="alert">{error}</p>
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
                    </p>
                  </div>
                  <button
                    className="secondary-action-button"
                    type="button"
                    aria-label={
                      'Edit visit note from ' + encounter.visit_date +
                      ': ' + encounter.reason_for_visit
                    }
                    onClick={() => setEditing(encounter)}
                  >
                    Edit
                  </button>
                </div>

                <details className="encounter-details">
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
                  </div>
                </details>
              </article>
            ))}
          </div>
        )}
    </section>
  )
}

export default EncounterList
