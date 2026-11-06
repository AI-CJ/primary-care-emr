import { useEffect, useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { CareGoal } from '../types'

type CareGoalsProps = {
  patientId: number
}

function CareGoals({ patientId }: CareGoalsProps) {
  const [goals, setGoals] = useState<CareGoal[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [reloadCount, setReloadCount] = useState(0)
  const [showAddForm, setShowAddForm] = useState(false)
  const [title, setTitle] = useState('')
  const [targetDate, setTargetDate] = useState('')
  const [completingId, setCompletingId] = useState<number | null>(null)
  const [completionNote, setCompletionNote] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    async function loadGoals() {
      setIsLoading(true)
      setLoadError(null)
      setGoals([])

      try {
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/care-goals',
          { signal: controller.signal }
        )
        if (!response.ok) {
          throw new Error(await getApiErrorMessage(response))
        }
        const records: CareGoal[] = await response.json()
        if (!controller.signal.aborted) setGoals(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setLoadError(
            requestError instanceof Error
              ? requestError.message
              : 'Care goals could not be loaded.'
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadGoals()
    return () => controller.abort()
  }, [patientId, reloadCount])

  async function addGoal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedTitle = title.trim()
    if (!trimmedTitle) {
      setActionError('Enter a goal before saving.')
      return
    }

    setIsSaving(true)
    setActionError(null)
    try {
      const response = await fetch(
        API_BASE_URL + '/patients/' + patientId + '/care-goals',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: trimmedTitle,
            target_date: targetDate || null,
          }),
        }
      )
      if (!response.ok) {
        throw new Error(await getApiErrorMessage(response))
      }
      setTitle('')
      setTargetDate('')
      setShowAddForm(false)
      setReloadCount((count) => count + 1)
    } catch (requestError) {
      setActionError(
        requestError instanceof Error
          ? requestError.message
          : 'The care goal could not be saved.'
      )
    } finally {
      setIsSaving(false)
    }
  }

  async function completeGoal(event: FormEvent<HTMLFormElement>, goalId: number) {
    event.preventDefault()
    const trimmedNote = completionNote.trim()
    if (!trimmedNote) {
      setActionError('Enter an outcome before completing this goal.')
      return
    }

    setIsSaving(true)
    setActionError(null)
    try {
      const response = await fetch(
        API_BASE_URL + '/care-goals/' + goalId + '/complete',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ completion_note: trimmedNote }),
        }
      )
      if (!response.ok) {
        throw new Error(await getApiErrorMessage(response))
      }
      setCompletingId(null)
      setCompletionNote('')
      setReloadCount((count) => count + 1)
    } catch (requestError) {
      setActionError(
        requestError instanceof Error
          ? requestError.message
          : 'The care goal could not be completed.'
      )
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section className="overview-card care-goal-card" aria-labelledby="care-goals-heading">
      <div className="overview-card-header">
        <h2 id="care-goals-heading">Care Goals</h2>
        <button
          className="secondary-action-button"
          type="button"
          disabled={isSaving}
          onClick={() => {
            setShowAddForm((show) => !show)
            setCompletingId(null)
            setActionError(null)
          }}
        >
          {showAddForm ? 'Close Form' : '+ Add Goal'}
        </button>
      </div>

      {showAddForm && (
        <form className="care-goal-form" onSubmit={addGoal}>
          <label className="form-field">
            <span>Goal *</span>
            <input
              type="text"
              required
              maxLength={200}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Walk for 20 minutes after lunch"
            />
          </label>
          <label className="form-field">
            <span>Target date (optional)</span>
            <input
              type="date"
              value={targetDate}
              onChange={(event) => setTargetDate(event.target.value)}
            />
          </label>
          <div className="care-goal-actions">
            <button className="save-patient-button" type="submit" disabled={isSaving}>
              {isSaving ? 'Saving...' : 'Save Goal'}
            </button>
            <button
              className="secondary-action-button"
              type="button"
              disabled={isSaving}
              onClick={() => {
                setShowAddForm(false)
                setActionError(null)
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {actionError && <p className="form-error" role="alert">{actionError}</p>}
      {isLoading && <p role="status">Loading care goals...</p>}
      {loadError && (
        <div>
          <p className="form-error" role="alert">{loadError}</p>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setReloadCount((count) => count + 1)}
          >
            Try Again
          </button>
        </div>
      )}
      {!isLoading && !loadError && goals.length === 0 && (
        <p>No care goals recorded yet.</p>
      )}
      {!isLoading && !loadError && goals.length > 0 && (
        <ul className="care-goal-list">
          {goals.map((goal) => (
            <li className="care-goal-row" key={goal.id}>
              <div className="care-goal-header">
                <strong className="care-goal-title">{goal.title}</strong>
                <span className="care-goal-status">
                  {goal.status === 'active' ? 'Active' : 'Completed'}
                </span>
              </div>
              <p className="care-goal-meta">
                Added <time dateTime={goal.created_at}>{goal.created_at.slice(0, 10)}</time>
                {goal.target_date && (
                  <>
                    {' · '}Target <time dateTime={goal.target_date}>{goal.target_date}</time>
                  </>
                )}
                {goal.completed_at && (
                  <>
                    {' · '}Completed <time dateTime={goal.completed_at}>
                      {goal.completed_at.slice(0, 10)}
                    </time>
                  </>
                )}
              </p>
              {goal.completion_note && (
                <p className="care-goal-notes">Outcome: {goal.completion_note}</p>
              )}
              {goal.status === 'active' && completingId !== goal.id && (
                <button
                  className="secondary-action-button care-goal-complete-button"
                  type="button"
                  disabled={isSaving}
                  aria-label={'Complete goal: ' + goal.title}
                  onClick={() => {
                    setShowAddForm(false)
                    setCompletingId(goal.id)
                    setCompletionNote('')
                    setActionError(null)
                  }}
                >
                  Mark Complete
                </button>
              )}
              {completingId === goal.id && goal.status === 'active' && (
                <form
                  className="care-goal-form"
                  onSubmit={(event) => void completeGoal(event, goal.id)}
                >
                  <label className="form-field">
                    <span>Outcome *</span>
                    <textarea
                      required
                      maxLength={2000}
                      rows={3}
                      value={completionNote}
                      onChange={(event) => setCompletionNote(event.target.value)}
                      placeholder="Describe how this goal was met."
                    />
                  </label>
                  <div className="care-goal-actions">
                    <button className="save-patient-button" type="submit" disabled={isSaving}>
                      {isSaving ? 'Saving...' : 'Complete Goal'}
                    </button>
                    <button
                      className="secondary-action-button"
                      type="button"
                      disabled={isSaving}
                      onClick={() => {
                        setCompletingId(null)
                        setActionError(null)
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default CareGoals
