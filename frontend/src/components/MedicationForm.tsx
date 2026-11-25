import { DiagnosisIndicationPicker } from './DiagnosisIndications'
import ReferencePicker, { type ReferenceChoice } from './ReferencePicker'
import { useState, type FormEvent } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type {
  Medication,
  MedicationInput,
  MedicationStatus,
} from '../types'

type MedicationFormProps = {
  patientId: number
  medication?: Medication
  onSaved: () => void
  onCancel: () => void
}

function MedicationForm({
  patientId,
  medication,
  onSaved,
  onCancel,
}: MedicationFormProps) {
  const [status, setStatus] = useState<MedicationStatus>(
    medication?.status ?? 'active'
  )
  const [name, setName] = useState(medication?.name ?? '')
  const [selected, setSelected] = useState<ReferenceChoice | null>(medication?.rxnorm_cui ? {
    code: medication.rxnorm_cui, name: medication.name, kind: medication.rxnorm_kind ?? '',
    release: medication.rxnorm_release ?? 'Historical reference',
  } : null)
  const [problemIds, setProblemIds] = useState(medication?.indications?.map(item => item.problem_id) ?? [])
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function optionalText(formData: FormData, name: string): string | null {
    const value = String(formData.get(name) ?? '').trim()
    return value || null
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setIsSaving(true)

    const formData = new FormData(event.currentTarget)

    const medicationData: MedicationInput = {
      name: name.trim(),
      rxnorm_cui: selected?.code ?? null,
      problem_ids: problemIds,
      strength: optionalText(formData, 'strength'),
      dose: optionalText(formData, 'dose'),
      route: optionalText(formData, 'route'),
      frequency: optionalText(formData, 'frequency'),
      status,
      start_date: optionalText(formData, 'start_date'),
      end_date:
        status === 'active' ? null : optionalText(formData, 'end_date'),
      instructions: optionalText(formData, 'instructions'),
    }

    const url = medication
      ? API_BASE_URL + '/medications/' + medication.id
      : API_BASE_URL + '/patients/' + patientId + '/medications'

    try {
      const response = await apiFetch(url, {
        method: medication ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(medicationData),
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
    <form className="medication-form" onSubmit={handleSubmit}>
      <ReferencePicker kind="rxnorm" label="Medication *" name="name" required
        value={name} selected={selected} disabled={isSaving}
        onChange={value => { setName(value); setSelected(null) }}
        onSelect={choice => { setName(choice.name); setSelected(choice) }} />
      {!selected && name.trim() && <p className="diagnosis-help">No RxNorm code selected. The medication will be recorded as uncoded text.</p>}

      <DiagnosisIndicationPicker patientId={patientId} selected={problemIds} onChange={setProblemIds} disabled={isSaving} />

      <label className="form-field">
        <span>Strength</span>
        <input
          name="strength"
          type="text"
          maxLength={100}
          placeholder="10 mg"
          defaultValue={medication?.strength ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Dose</span>
        <input
          name="dose"
          type="text"
          maxLength={100}
          placeholder="1 tablet"
          defaultValue={medication?.dose ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Route</span>
        <input
          name="route"
          type="text"
          maxLength={100}
          placeholder="Oral"
          defaultValue={medication?.route ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Frequency</span>
        <input
          name="frequency"
          type="text"
          maxLength={100}
          placeholder="Once daily"
          defaultValue={medication?.frequency ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Status *</span>
        <select
          name="status"
          value={status}
          onChange={(event) =>
            setStatus(event.target.value as MedicationStatus)
          }
        >
          <option value="active">Active</option>
          <option value="completed">Completed</option>
          <option value="discontinued">Discontinued</option>
        </select>
      </label>

      <label className="form-field">
        <span>Start date</span>
        <input
          name="start_date"
          type="date"
          defaultValue={medication?.start_date ?? ''}
        />
      </label>

      {status !== 'active' && (
        <label className="form-field">
          <span>End date</span>
          <input
            name="end_date"
            type="date"
            defaultValue={medication?.end_date ?? ''}
          />
        </label>
      )}

      <label className="form-field">
        <span>Instructions</span>
        <textarea
          name="instructions"
          rows={4}
          maxLength={1000}
          defaultValue={medication?.instructions ?? ''}
        />
      </label>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <div className="medication-form-actions">
        <button
          className="save-patient-button"
          type="submit"
          disabled={isSaving}
        >
          {isSaving
            ? 'Saving...'
            : medication
              ? 'Save Changes'
              : 'Add Medication'}
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

export default MedicationForm
