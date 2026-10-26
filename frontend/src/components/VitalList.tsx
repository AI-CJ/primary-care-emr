import { useCallback, useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Vital } from '../types'
import VitalForm from './VitalForm'

type VitalListProps = {
  patientId: number
}

function measurementLabels(vital: Vital): string[] {
  const labels: string[] = []
  if (vital.systolic_bp !== null && vital.diastolic_bp !== null) {
    labels.push('BP ' + vital.systolic_bp + '/' + vital.diastolic_bp + ' mmHg')
  }
  if (vital.heart_rate !== null) {
    labels.push('Heart rate ' + vital.heart_rate + ' bpm')
  }
  if (vital.respiratory_rate !== null) {
    labels.push('Respiratory rate ' + vital.respiratory_rate + '/min')
  }
  if (vital.temperature_c !== null) {
    labels.push('Temperature ' + vital.temperature_c + ' °C')
  }
  if (vital.oxygen_saturation !== null) {
    labels.push('SpO₂ ' + vital.oxygen_saturation + '%')
  }
  if (vital.height_cm !== null) {
    labels.push('Height ' + vital.height_cm + ' cm')
  }
  if (vital.weight_kg !== null) {
    labels.push('Weight ' + vital.weight_kg + ' kg')
  }
  return labels
}

function VitalList({ patientId }: VitalListProps) {
  const [vitals, setVitals] = useState<Vital[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [editingVital, setEditingVital] = useState<Vital | null>(null)

  const loadVitals = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    setVitals([])
    try {
      const response = await fetch(
        API_BASE_URL + '/patients/' + patientId + '/vitals'
      )
      if (!response.ok) {
        setError(await getApiErrorMessage(response))
        return
      }
      const data: Vital[] = await response.json()
      setVitals(data)
    } catch (requestError) {
      console.error(requestError)
      setError('Vitals could not be loaded.')
    } finally {
      setIsLoading(false)
    }
  }, [patientId])

  useEffect(() => {
    void loadVitals()
  }, [loadVitals])

  function finishEditing() {
    setIsAdding(false)
    setEditingVital(null)
    void loadVitals()
  }

  return (
    <section className="overview-card vital-card">
      <div className="overview-card-header">
        <h2>Vitals</h2>
        {!isAdding && !editingVital && (
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setIsAdding(true)}
          >
            + Record Vitals
          </button>
        )}
      </div>
      {isAdding && (
        <VitalForm
          patientId={patientId}
          onSaved={finishEditing}
          onCancel={() => setIsAdding(false)}
        />
      )}
      {editingVital && (
        <VitalForm
          patientId={patientId}
          vital={editingVital}
          onSaved={finishEditing}
          onCancel={() => setEditingVital(null)}
        />
      )}
      {!isAdding && !editingVital && isLoading && <p>Loading vitals...</p>}
      {!isAdding && !editingVital && error && (
        <p className="form-error" role="alert">{error}</p>
      )}
      {!isAdding && !editingVital && !isLoading && !error &&
        vitals.length === 0 && <p>No vitals recorded yet.</p>}
      {!isAdding && !editingVital && !isLoading && !error &&
        vitals.length > 0 && (
          <div className="vital-list">
            {vitals.map((vital) => (
              <div className="vital-row" key={vital.id}>
                <div>
                  <strong>{vital.recorded_on}</strong>
                  <p className="vital-meta">
                    {measurementLabels(vital).join(' · ')}
                  </p>
                  {vital.notes && (
                    <p className="vital-notes">{vital.notes}</p>
                  )}
                </div>
                <button
                  className="secondary-action-button"
                  type="button"
                  onClick={() => setEditingVital(vital)}
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

export default VitalList
