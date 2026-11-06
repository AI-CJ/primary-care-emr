import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import './CareGoalProgress.css'

type ProgressEntry = {
  id: number
  goal_id: number
  note: string
  recorded_at: string
}

type CareGoalProgressProps = {
  goalId: number
  goalTitle: string
  isActive: boolean
}

function CareGoalProgress({ goalId, goalTitle, isActive }: CareGoalProgressProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [entries, setEntries] = useState<ProgressEntry[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [refreshCount, setRefreshCount] = useState(0)
  const panelId = 'care-goal-progress-' + goalId

  useEffect(() => {
    if (!isOpen) return

    const controller = new AbortController()
    setEntries(null)
    setLoadError(null)

    async function loadProgress() {
      try {
        const response = await fetch(API_BASE_URL + '/care-goals/' + goalId + '/progress', {
          signal: controller.signal,
        })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: ProgressEntry[] = await response.json()
        if (!controller.signal.aborted) setEntries(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setLoadError(
            requestError instanceof Error
              ? requestError.message
              : 'Progress updates could not be loaded.',
          )
        }
      }
    }

    void loadProgress()
    return () => controller.abort()
  }, [goalId, isOpen, refreshCount])

  async function saveProgress(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedNote = note.trim()
    if (!trimmedNote) {
      setSaveError('Enter a progress note before saving.')
      return
    }

    setIsSaving(true)
    setSaveError(null)
    try {
      const response = await fetch(API_BASE_URL + '/care-goals/' + goalId + '/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: trimmedNote }),
      })
      if (!response.ok) throw new Error(await getApiErrorMessage(response))

      setNote('')
      setRefreshCount((count) => count + 1)
    } catch (requestError) {
      setSaveError(
        requestError instanceof Error
          ? requestError.message
          : 'The progress update could not be saved.',
      )
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="care-goal-progress">
      <button
        className="secondary-action-button"
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={() => {
          setIsOpen((open) => !open)
          setSaveError(null)
        }}
      >
        {isOpen ? 'Hide Progress' : 'View Progress'}
      </button>
      {isOpen && (
        <div className="care-goal-progress-panel" id={panelId}>
          <h3>Progress for {goalTitle}</h3>
          {entries === null && !loadError && (
            <p role="status">Loading progress updates...</p>
          )}
          {loadError && (
            <div>
              <p className="form-error" role="alert">{loadError}</p>
              <button
                className="secondary-action-button"
                type="button"
                onClick={() => setRefreshCount((count) => count + 1)}
              >
                Try Again
              </button>
            </div>
          )}
          {entries && entries.length === 0 && (
            <p>No progress updates recorded yet.</p>
          )}
          {entries && entries.length > 0 && (
            <ol className="care-goal-progress-list">
              {entries.map((entry) => (
                <li className="care-goal-progress-entry" key={entry.id}>
                  <time dateTime={entry.recorded_at}>
                    {new Date(entry.recorded_at).toLocaleString()}
                  </time>
                  <p>{entry.note}</p>
                </li>
              ))}
            </ol>
          )}
          {isActive && (
            <form className="care-goal-form" onSubmit={(event: FormEvent<HTMLFormElement>) => void saveProgress(event)}>
              <label className="form-field">
                <span>New progress note *</span>
                <textarea
                  required
                  maxLength={2000}
                  rows={3}
                  value={note}
                  onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setNote(event.target.value)}
                  placeholder="Describe progress toward this goal."
                />
              </label>
              {saveError && <p className="form-error" role="alert">{saveError}</p>}
              <div className="care-goal-actions">
                <button className="save-patient-button" type="submit" disabled={isSaving}>
                  {isSaving ? 'Saving...' : 'Add Progress Update'}
                </button>
              </div>
            </form>
          )}
          {!isActive && (
            <p className="care-goal-progress-closed">Completed goals retain their progress history.</p>
          )}
        </div>
      )}
    </div>
  )
}

export default CareGoalProgress
