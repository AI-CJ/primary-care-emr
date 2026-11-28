import DiagnosisIndications from './DiagnosisIndications'
import { useCallback, useEffect, useId, useState } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type { Medication } from '../types'
import MedicationForm from './MedicationForm'
import { useInlineEditorFocus } from '../useInlineEditorFocus'

type MedicationListProps = {
  patientId: number
}

function statusLabel(status: Medication['status']): string {
  if (status === 'completed') {
    return 'Completed'
  }

  if (status === 'discontinued') {
    return 'Discontinued'
  }

  return 'Active'
}

function MedicationList({ patientId }: MedicationListProps) {
  const [medications, setMedications] = useState<Medication[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [editingMedication, setEditingMedication] =
    useState<Medication | null>(null)
  const [message, setMessage] = useState('')
  const headingId = useId()
  const { containerRef, rememberTrigger, returnToHeading } = useInlineEditorFocus(isAdding || editingMedication !== null)

  const loadMedications = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiFetch(
        API_BASE_URL + '/patients/' + patientId + '/medications'
      )

      if (!response.ok) {
        setError(await getApiErrorMessage(response))
        return
      }

      const data: Medication[] = await response.json()
      setMedications(data)
    } catch (requestError) {
      console.error(requestError)
      setError('Medications could not be loaded.')
    } finally {
      setIsLoading(false)
    }
  }, [patientId])

  useEffect(() => {
    let active = true
    queueMicrotask(() => {
      if (active) void loadMedications()
    })
    return () => { active = false }
  }, [loadMedications])

  function finishEditing() {
    returnToHeading()
    setIsAdding(false)
    setEditingMedication(null)
    setMessage('Medication saved.')
    void loadMedications()
  }

  return (
    <section className="overview-card medication-card" ref={containerRef} aria-labelledby={headingId}>
      <div className="overview-card-header">
        <h2 id={headingId}>Medications</h2>

        {!isAdding && !editingMedication && (
          <button
            className="secondary-action-button"
            type="button"
            data-editor-trigger="add"
            onClick={() => { rememberTrigger('add'); setMessage(''); setIsAdding(true) }}
          >
            + Add Medication
          </button>
        )}
      </div>

      <p role="status" aria-atomic="true" className="form-success editor-status">{message}</p>

      {isAdding && (
        <MedicationForm
          patientId={patientId}
          onSaved={finishEditing}
          onCancel={() => setIsAdding(false)}
        />
      )}

      {editingMedication && (
        <MedicationForm
          patientId={patientId}
          medication={editingMedication}
          onSaved={finishEditing}
          onCancel={() => setEditingMedication(null)}
        />
      )}

      {!isAdding && !editingMedication && isLoading && (
        <p role="status">Loading medications...</p>
      )}

      {!isAdding && !editingMedication && error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {!isAdding &&
        !editingMedication &&
        !isLoading &&
        !error &&
        medications.length === 0 && <p>No medications recorded yet.</p>}

      {!isAdding &&
        !editingMedication &&
        !isLoading &&
        !error &&
        medications.length > 0 && (
          <div className="medication-list">
            {medications.map((medication) => (
              <div className="medication-row" key={medication.id}>
                <div>
                  <strong>
                    {medication.name}
                    {medication.strength && ' ' + medication.strength}
                  </strong>

                  <p className="medication-meta">
                    {statusLabel(medication.status)}
                    {medication.dose && ' · ' + medication.dose}
                    {medication.route && ' · ' + medication.route}
                    {medication.frequency && ' · ' + medication.frequency}
                  </p>

                  <p className="medication-meta">{medication.rxnorm_cui
                    ? <>RxCUI <span className="diagnosis-code">{medication.rxnorm_cui}</span></>
                    : 'No RxNorm code recorded'}</p>
                  <DiagnosisIndications records={medication.indications} />

                  {(medication.start_date || medication.end_date) && (
                    <p className="medication-meta">
                      {medication.start_date &&
                        'Started ' + medication.start_date}
                      {medication.start_date &&
                        medication.end_date &&
                        ' · '}
                      {medication.end_date &&
                        'Ended ' + medication.end_date}
                    </p>
                  )}

                  {medication.instructions && (
                    <p className="medication-instructions">
                      {medication.instructions}
                    </p>
                  )}
                </div>

                <button
                  className="secondary-action-button"
                  type="button"
                  aria-label={'Edit medication: ' + medication.name + (medication.strength ? ' ' + medication.strength : '')}
                  data-editor-trigger={'medication-' + medication.id}
                  onClick={() => { rememberTrigger('medication-' + medication.id); setMessage(''); setEditingMedication(medication) }}
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

export default MedicationList
