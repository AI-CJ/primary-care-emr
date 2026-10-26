import { useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Problem, ProblemInput, ProblemStatus } from '../types'

type ProblemFormProps = {
  patientId: number
  problem?: Problem
  onSaved: () => void
  onCancel: () => void
}

function ProblemForm({ patientId, problem, onSaved, onCancel }: ProblemFormProps) {
  const [status, setStatus] = useState<ProblemStatus>(problem?.status ?? 'active')
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
    const problemData: ProblemInput = {
      name: String(formData.get('name') ?? '').trim(),
      status,
      onset_date: optionalText(formData, 'onset_date'),
      resolved_date:
        status === 'resolved' ? optionalText(formData, 'resolved_date') : null,
      notes: optionalText(formData, 'notes'),
    }

    const url = problem
      ? API_BASE_URL + '/problems/' + problem.id
      : API_BASE_URL + '/patients/' + patientId + '/problems'

    try {
      const response = await fetch(url, {
        method: problem ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(problemData),
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
    <form className="problem-form" onSubmit={handleSubmit}>
      <label className="form-field">
        <span>Problem *</span>
        <input
          name="name"
          type="text"
          required
          maxLength={200}
          defaultValue={problem?.name ?? ''}
        />
      </label>

      <label className="form-field">
        <span>Status *</span>
        <select
          name="status"
          value={status}
          onChange={(event) => setStatus(event.target.value as ProblemStatus)}
        >
          <option value="active">Active</option>
          <option value="resolved">Resolved</option>
        </select>
      </label>

      <label className="form-field">
        <span>Onset date</span>
        <input
          name="onset_date"
          type="date"
          defaultValue={problem?.onset_date ?? ''}
        />
      </label>

      {status === 'resolved' && (
        <label className="form-field">
          <span>Resolved date</span>
          <input
            name="resolved_date"
            type="date"
            defaultValue={problem?.resolved_date ?? ''}
          />
        </label>
      )}

      <label className="form-field">
        <span>Notes</span>
        <textarea
          name="notes"
          rows={4}
          maxLength={1000}
          defaultValue={problem?.notes ?? ''}
        />
      </label>

      {error && <p className="form-error" role="alert">{error}</p>}

      <div className="problem-form-actions">
        <button className="save-patient-button" type="submit" disabled={isSaving}>
          {isSaving ? 'Saving...' : problem ? 'Save Changes' : 'Add Problem'}
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

export default ProblemForm
