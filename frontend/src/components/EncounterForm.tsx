import { useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Encounter, EncounterInput } from '../types'

type EncounterFormProps = {
  patientId: number
  encounter?: Encounter
  onSaved: () => void
  onCancel: () => void
}

function EncounterForm({
  patientId,
  encounter,
  onSaved,
  onCancel,
}: EncounterFormProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function optionalText(formData: FormData, name: string): string | null {
    const value = String(formData.get(name) ?? '').trim()
    return value || null
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    const formData = new FormData(event.currentTarget)
    const encounterData: EncounterInput = {
      visit_date: String(formData.get('visit_date') ?? ''),
      reason_for_visit: String(formData.get('reason_for_visit') ?? '').trim(),
      subjective: optionalText(formData, 'subjective'),
      objective: optionalText(formData, 'objective'),
      assessment: optionalText(formData, 'assessment'),
      plan: optionalText(formData, 'plan'),
    }

    if (
      !encounterData.subjective &&
      !encounterData.objective &&
      !encounterData.assessment &&
      !encounterData.plan
    ) {
      setError('Complete at least one visit note section.')
      return
    }

    setIsSaving(true)
    const url = encounter
      ? API_BASE_URL + '/encounters/' + encounter.id
      : API_BASE_URL + '/patients/' + patientId + '/encounters'

    try {
      const response = await fetch(url, {
        method: encounter ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(encounterData),
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
    <form className="encounter-form" onSubmit={handleSubmit}>
      <p className="encounter-help">
        Development only: enter fictional patient information, never real records.
      </p>

      <label className="form-field">
        <span>Visit date *</span>
        <input
          type="date"
          name="visit_date"
          required
          defaultValue={encounter?.visit_date ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Reason for visit *</span>
        <input
          type="text"
          name="reason_for_visit"
          required
          maxLength={200}
          defaultValue={encounter?.reason_for_visit ?? ''}
        />
      </label>

      <p className="encounter-help">Complete at least one note section.</p>

      <label className="form-field">
        <span>Subjective</span>
        <textarea
          name="subjective"
          rows={4}
          maxLength={4000}
          defaultValue={encounter?.subjective ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Objective</span>
        <textarea
          name="objective"
          rows={4}
          maxLength={4000}
          defaultValue={encounter?.objective ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Assessment</span>
        <textarea
          name="assessment"
          rows={4}
          maxLength={4000}
          defaultValue={encounter?.assessment ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Plan</span>
        <textarea
          name="plan"
          rows={4}
          maxLength={4000}
          defaultValue={encounter?.plan ?? ''}
        />
      </label>

      {error && <p className="form-error" role="alert">{error}</p>}

      <div className="encounter-form-actions">
        <button
          className="save-patient-button"
          type="submit"
          disabled={isSaving}
        >
          {isSaving ? 'Saving...' : encounter ? 'Save Changes' : 'Save Visit Note'}
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

export default EncounterForm
