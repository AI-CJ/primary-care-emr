import { useCallback, useEffect, useId, useState } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type { Allergy } from '../types'
import AllergyForm from './AllergyForm'
import { useInlineEditorFocus } from '../useInlineEditorFocus'

type AllergyListProps = {
  patientId: number
  onChanged?: () => void
}

function severityLabel(severity: Allergy['severity']): string {
  if (severity === 'mild') {
    return 'Mild'
  }

  if (severity === 'moderate') {
    return 'Moderate'
  }

  if (severity === 'severe') {
    return 'Severe'
  }

  return 'Severity unknown'
}

function AllergyList({ patientId, onChanged }: AllergyListProps) {
  const [allergies, setAllergies] = useState<Allergy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [editingAllergy, setEditingAllergy] = useState<Allergy | null>(null)
  const [message, setMessage] = useState('')
  const headingId = useId()
  const { containerRef, rememberTrigger, returnToHeading } = useInlineEditorFocus(isAdding || editingAllergy !== null)

  const loadAllergies = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiFetch(
        API_BASE_URL + '/patients/' + patientId + '/allergies'
      )

      if (!response.ok) {
        setError(await getApiErrorMessage(response))
        return
      }

      const data: Allergy[] = await response.json()
      setAllergies(data)
    } catch (requestError) {
      console.error(requestError)
      setError('Allergies could not be loaded.')
    } finally {
      setIsLoading(false)
    }
  }, [patientId])

  useEffect(() => {
    let active = true
    queueMicrotask(() => {
      if (active) void loadAllergies()
    })
    return () => { active = false }
  }, [loadAllergies])

  function finishEditing() {
    returnToHeading()
    setIsAdding(false)
    setEditingAllergy(null)
    setMessage('Allergy saved.')
    onChanged?.()
    void loadAllergies()
  }

  return (
    <section className="overview-card allergy-card" ref={containerRef} aria-labelledby={headingId}>
      <div className="overview-card-header">
        <h2 id={headingId}>Allergies</h2>

        {!isAdding && !editingAllergy && (
          <button
            className="secondary-action-button"
            type="button"
            data-editor-trigger="add"
            onClick={() => { rememberTrigger('add'); setMessage(''); setIsAdding(true) }}
          >
            + Add Allergy
          </button>
        )}
      </div>

      <p role="status" aria-atomic="true" className="form-success editor-status">{message}</p>

      {isAdding && (
        <AllergyForm
          patientId={patientId}
          onSaved={finishEditing}
          onCancel={() => setIsAdding(false)}
        />
      )}

      {editingAllergy && (
        <AllergyForm
          patientId={patientId}
          allergy={editingAllergy}
          onSaved={finishEditing}
          onCancel={() => setEditingAllergy(null)}
        />
      )}

      {!isAdding && !editingAllergy && isLoading && (
        <p role="status">Loading allergies...</p>
      )}

      {!isAdding && !editingAllergy && error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {!isAdding &&
        !editingAllergy &&
        !isLoading &&
        !error &&
        allergies.length === 0 && <p>No allergies recorded yet.</p>}

      {!isAdding &&
        !editingAllergy &&
        !isLoading &&
        !error &&
        allergies.length > 0 && (
          <div className="allergy-list">
            {allergies.map((allergy) => (
              <div className="allergy-row" key={allergy.id}>
                <div>
                  <strong>{allergy.allergen}</strong>

                  <p className="allergy-meta">
                    {allergy.status === 'active' ? 'Active' : 'Inactive'}
                    {' · '}
                    {severityLabel(allergy.severity)}
                    {allergy.onset_date && ' · Onset ' + allergy.onset_date}
                  </p>

                  {allergy.reaction && (
                    <p className="allergy-reaction">
                      Reaction: {allergy.reaction}
                    </p>
                  )}

                  {allergy.notes && (
                    <p className="allergy-notes">{allergy.notes}</p>
                  )}
                </div>

                <button
                  className="secondary-action-button"
                  type="button"
                  aria-label={'Edit allergy: ' + allergy.allergen}
                  data-editor-trigger={'allergy-' + allergy.id}
                  onClick={() => { rememberTrigger('allergy-' + allergy.id); setMessage(''); setEditingAllergy(allergy) }}
                >
                  Edit
                </button>
              </div>
            ))}
          </div>
        )}
    </section>
  )
}

export default AllergyList
