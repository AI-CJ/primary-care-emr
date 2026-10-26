import { useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Vital, VitalInput } from '../types'

type VitalFormProps = {
  patientId: number
  vital?: Vital
  onSaved: () => void
  onCancel: () => void
}

type NumericVitalKey = Exclude<keyof VitalInput, 'recorded_on' | 'notes'>

const numericFields: {
  name: NumericVitalKey
  label: string
  min: string
  max: string
  step: string
}[] = [
  { name: 'systolic_bp', label: 'Systolic BP (mmHg)', min: '1', max: '400', step: '1' },
  { name: 'diastolic_bp', label: 'Diastolic BP (mmHg)', min: '1', max: '300', step: '1' },
  { name: 'heart_rate', label: 'Heart rate (bpm)', min: '1', max: '350', step: '1' },
  { name: 'respiratory_rate', label: 'Respiratory rate (breaths/min)', min: '1', max: '150', step: '1' },
  { name: 'temperature_c', label: 'Temperature (°C)', min: '0', max: '60', step: '0.1' },
  { name: 'oxygen_saturation', label: 'Oxygen saturation (%)', min: '0', max: '100', step: '1' },
  { name: 'height_cm', label: 'Height (cm)', min: '0.1', max: '300', step: '0.1' },
  { name: 'weight_kg', label: 'Weight (kg)', min: '0.1', max: '1000', step: '0.1' },
]

function localToday(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return now.getFullYear() + '-' + month + '-' + day
}

function optionalNumber(formData: FormData, name: string): number | null {
  const value = String(formData.get(name) ?? '').trim()
  return value === '' ? null : Number(value)
}

function VitalForm({ patientId, vital, onSaved, onCancel }: VitalFormProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const today = localToday()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    const formData = new FormData(event.currentTarget)
    const notes = String(formData.get('notes') ?? '').trim()
    const vitalData: VitalInput = {
      recorded_on: String(formData.get('recorded_on') ?? ''),
      systolic_bp: optionalNumber(formData, 'systolic_bp'),
      diastolic_bp: optionalNumber(formData, 'diastolic_bp'),
      heart_rate: optionalNumber(formData, 'heart_rate'),
      respiratory_rate: optionalNumber(formData, 'respiratory_rate'),
      temperature_c: optionalNumber(formData, 'temperature_c'),
      oxygen_saturation: optionalNumber(formData, 'oxygen_saturation'),
      height_cm: optionalNumber(formData, 'height_cm'),
      weight_kg: optionalNumber(formData, 'weight_kg'),
      notes: notes || null,
    }

    if ((vitalData.systolic_bp === null) !== (vitalData.diastolic_bp === null)) {
      setError('Enter both systolic and diastolic blood pressure.')
      return
    }
    if (
      vitalData.systolic_bp !== null &&
      vitalData.diastolic_bp !== null &&
      vitalData.systolic_bp < vitalData.diastolic_bp
    ) {
      setError('Systolic blood pressure cannot be below diastolic.')
      return
    }
    if (numericFields.every(({ name }) => vitalData[name] === null)) {
      setError('Enter at least one vital measurement.')
      return
    }

    const url = vital
      ? API_BASE_URL + '/vitals/' + vital.id
      : API_BASE_URL + '/patients/' + patientId + '/vitals'
    setIsSaving(true)
    try {
      const response = await fetch(url, {
        method: vital ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(vitalData),
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
    <form className="vital-form" onSubmit={handleSubmit}>
      <label className="form-field">
        <span>Recorded on *</span>
        <input
          name="recorded_on"
          type="date"
          required
          max={today}
          defaultValue={vital?.recorded_on ?? today}
        />
      </label>
      <div className="form-grid">
        {numericFields.map((field) => (
          <label className="form-field" key={field.name}>
            <span>{field.label}</span>
            <input
              name={field.name}
              type="number"
              min={field.min}
              max={field.max}
              step={field.step}
              defaultValue={vital?.[field.name] ?? ''}
            />
          </label>
        ))}
      </div>
      <label className="form-field">
        <span>Notes</span>
        <textarea
          name="notes"
          rows={3}
          maxLength={1000}
          defaultValue={vital?.notes ?? ''}
        />
      </label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="vital-form-actions">
        <button
          className="save-patient-button"
          type="submit"
          disabled={isSaving}
        >
          {isSaving ? 'Saving...' : vital ? 'Save Changes' : 'Save Vitals'}
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

export default VitalForm
