import { useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type {
  Allergy,
  AllergyInput,
  AllergySeverity,
  AllergyStatus,
} from '../types'

type AllergyFormProps = {
  patientId: number
  allergy?: Allergy
  onSaved: () => void
  onCancel: () => void
}

function AllergyForm({
  patientId,
  allergy,
  onSaved,
  onCancel,
}: AllergyFormProps) {
  const [severity, setSeverity] = useState<AllergySeverity>(
    allergy?.severity ?? 'unknown'
  )
  const [status, setStatus] = useState<AllergyStatus>(
    allergy?.status ?? 'active'
  )
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

    const allergyData: AllergyInput = {
      allergen: String(formData.get('allergen') ?? '').trim(),
      reaction: optionalText(formData, 'reaction'),
      severity,
      status,
      onset_date: optionalText(formData, 'onset_date'),
      notes: optionalText(formData, 'notes'),
    }

    const url = allergy
      ? API_BASE_URL + '/allergies/' + allergy.id
      : API_BASE_URL + '/patients/' + patientId + '/allergies'

    try {
      const response = await fetch(url, {
        method: allergy ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(allergyData),
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
    <form className="allergy-form" onSubmit={handleSubmit}>
      <label className="form-field">
        <span>Allergen *</span>
        <input
          name="allergen"
          type="text"
          required
          maxLength={200}
          placeholder="Penicillin"
          defaultValue={allergy?.allergen ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Reaction</span>
        <input
          name="reaction"
          type="text"
          maxLength={300}
          placeholder="Hives"
          defaultValue={allergy?.reaction ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Severity *</span>
        <select
          name="severity"
          value={severity}
          onChange={(event) =>
            setSeverity(event.target.value as AllergySeverity)
          }
        >
          <option value="unknown">Unknown</option>
          <option value="mild">Mild</option>
          <option value="moderate">Moderate</option>
          <option value="severe">Severe</option>
        </select>
      </label>

      <label className="form-field">
        <span>Status *</span>
        <select
          name="status"
          value={status}
          onChange={(event) =>
            setStatus(event.target.value as AllergyStatus)
          }
        >
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </label>

      <label className="form-field">
        <span>Onset date</span>
        <input
          name="onset_date"
          type="date"
          defaultValue={allergy?.onset_date ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Notes</span>
        <textarea
          name="notes"
          rows={4}
          maxLength={1000}
          defaultValue={allergy?.notes ?? ''}
        />
      </label>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <div className="allergy-form-actions">
        <button
          className="save-patient-button"
          type="submit"
          disabled={isSaving}
        >
          {isSaving
            ? 'Saving...'
            : allergy
              ? 'Save Changes'
              : 'Add Allergy'}
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

export default AllergyForm
