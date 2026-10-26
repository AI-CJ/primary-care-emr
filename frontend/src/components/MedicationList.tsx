import { useCallback, useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Medication } from '../types'
import MedicationForm from './MedicationForm'

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

  const loadMedications = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(
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
    void loadMedications()
  }, [loadMedications])

  function finishEditing() {
    setIsAdding(false)
    setEditingMedication(null)
    void loadMedications()
  }

  return (
    <section className="overview-card medication-card">
      <div className="overview-card-header">
        <h2>Medications</h2>

        {!isAdding && !editingMedication && (
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setIsAdding(true)}
          >
            + Add Medication
          </button>
        )}
      </div>

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
        <p>Loading medications...</p>
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
                  onClick={() => setEditingMedication(medication)}
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
