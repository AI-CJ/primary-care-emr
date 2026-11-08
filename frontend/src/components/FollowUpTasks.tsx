import { useEffect, useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { CareGoal, FollowUpTask } from '../types'
import './FollowUpTasks.css'

type FollowUpTasksProps = {
  patientId: number
}

function FollowUpTasks({ patientId }: FollowUpTasksProps) {
  const [tasks, setTasks] = useState<FollowUpTask[]>([])
  const [goals, setGoals] = useState<CareGoal[] | null>(null)
  const [goalsError, setGoalsError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [reloadCount, setReloadCount] = useState(0)
  const [showAddForm, setShowAddForm] = useState(false)
  const [title, setTitle] = useState('')
  const [details, setDetails] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [selectedGoalId, setSelectedGoalId] = useState('')
  const [completingId, setCompletingId] = useState<number | null>(null)
  const [completionNote, setCompletionNote] = useState('')
  const [cancellingId, setCancellingId] = useState<number | null>(null)
  const [cancellationReason, setCancellationReason] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    async function loadTasks() {
      setIsLoading(true)
      setLoadError(null)
      setTasks([])

      try {
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/follow-up-tasks',
          { signal: controller.signal }
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: FollowUpTask[] = await response.json()
        if (!controller.signal.aborted) setTasks(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setLoadError(
            requestError instanceof Error
              ? requestError.message
              : 'Follow-up tasks could not be loaded.'
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadTasks()
    return () => controller.abort()
  }, [patientId, reloadCount])

  useEffect(() => {
    const controller = new AbortController()
    setGoals(null)
    setGoalsError(null)

    async function loadGoals() {
      try {
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/care-goals',
          { signal: controller.signal }
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: CareGoal[] = await response.json()
        if (!controller.signal.aborted) setGoals(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setGoalsError(
            requestError instanceof Error
              ? requestError.message
              : 'Care goals could not be loaded.'
          )
        }
      }
    }

    void loadGoals()
    return () => controller.abort()
  }, [patientId, reloadCount, showAddForm])

  async function addTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const taskTitle = title.trim()
    if (!taskTitle) {
      setActionError('Enter a task title before saving.')
      return
    }

    setIsSaving(true)
    setActionError(null)
    try {
      const response = await fetch(
        API_BASE_URL + '/patients/' + patientId + '/follow-up-tasks',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: taskTitle,
            details: details.trim() || null,
            due_date: dueDate || null,
            care_goal_id: selectedGoalId ? Number(selectedGoalId) : null,
          }),
        }
      )
      if (!response.ok) throw new Error(await getApiErrorMessage(response))

      setTitle('')
      setDetails('')
      setDueDate('')
      setSelectedGoalId('')
      setShowAddForm(false)
      setReloadCount((count) => count + 1)
    } catch (requestError) {
      setActionError(
        requestError instanceof Error
          ? requestError.message
          : 'The follow-up task could not be saved.'
      )
    } finally {
      setIsSaving(false)
    }
  }

  async function completeTask(event: FormEvent<HTMLFormElement>, taskId: number) {
    event.preventDefault()
    const note = completionNote.trim()
    if (!note) {
      setActionError('Enter an outcome before completing this task.')
      return
    }

    setIsSaving(true)
    setActionError(null)
    try {
      const response = await fetch(
        API_BASE_URL + '/follow-up-tasks/' + taskId + '/complete',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ completion_note: note }),
        }
      )
      if (!response.ok) throw new Error(await getApiErrorMessage(response))

      setCompletingId(null)
      setCompletionNote('')
      setReloadCount((count) => count + 1)
    } catch (requestError) {
      setActionError(
        requestError instanceof Error
          ? requestError.message
          : 'The task could not be completed.'
      )
    } finally {
      setIsSaving(false)
    }
  }

  async function cancelTask(event: FormEvent<HTMLFormElement>, taskId: number) {
    event.preventDefault()
    const reason = cancellationReason.trim()
    if (!reason) {
      setActionError('Enter a reason before cancelling this task.')
      return
    }

    setIsSaving(true)
    setActionError(null)
    try {
      const response = await fetch(
        API_BASE_URL + '/follow-up-tasks/' + taskId + '/cancel',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason }),
        }
      )
      if (!response.ok) throw new Error(await getApiErrorMessage(response))

      setCancellingId(null)
      setCancellationReason('')
      setReloadCount((count) => count + 1)
    } catch (requestError) {
      setActionError(
        requestError instanceof Error
          ? requestError.message
          : 'The task could not be cancelled.'
      )
    } finally {
      setIsSaving(false)
    }
  }

  const orderedTasks = [
    ...tasks.filter((task) => task.status === 'open'),
    ...tasks.filter((task) => task.status === 'completed'),
    ...tasks.filter((task) => task.status === 'cancelled'),
  ]

  return (
    <section className="overview-card follow-up-task-card" aria-labelledby="follow-up-tasks-heading">
      <div className="overview-card-header">
        <h2 id="follow-up-tasks-heading">Follow-up Tasks</h2>
        <button
          className="secondary-action-button"
          type="button"
          disabled={isSaving}
          onClick={() => {
            setShowAddForm((show) => !show)
            setSelectedGoalId('')
            setCompletingId(null)
            setCompletionNote('')
            setCancellingId(null)
            setCancellationReason('')
            setActionError(null)
          }}
        >
          {showAddForm ? 'Close Form' : '+ Add Task'}
        </button>
      </div>

      {showAddForm && (
        <form className="follow-up-task-form" onSubmit={(event) => void addTask(event)}>
          <label className="form-field">
            <span>Task *</span>
            <input
              type="text"
              required
              maxLength={200}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Call to arrange a follow-up appointment"
            />
          </label>
          <label className="form-field">
            <span>Details (optional)</span>
            <textarea
              rows={3}
              maxLength={2000}
              value={details}
              onChange={(event) => setDetails(event.target.value)}
            />
          </label>
          <label className="form-field">
            <span>Due date (optional)</span>
            <input
              type="date"
              value={dueDate}
              onChange={(event) => setDueDate(event.target.value)}
            />
          </label>
          <label className="form-field">
            <span>Care goal (optional)</span>
            <select
              value={selectedGoalId}
              disabled={isSaving || goals === null || goalsError !== null}
              onChange={(event) => setSelectedGoalId(event.target.value)}
            >
              <option value="">No care goal</option>
              {(goals ?? []).filter((goal) => goal.status === 'active').map((goal) => (
                <option key={goal.id} value={goal.id}>{goal.title}</option>
              ))}
            </select>
          </label>
          {goals === null && !goalsError && (
            <p role="status">Loading care goals...</p>
          )}
          {goalsError && (
            <p className="form-error" role="status">
              Could not load care goals: {goalsError} You can still save an unlinked task.
            </p>
          )}
          {goals !== null && goals.every((goal) => goal.status !== 'active') && (
            <p>No active care goals. Tasks can still be saved without a goal.</p>
          )}
          <div className="follow-up-task-actions">
            <button className="save-patient-button" type="submit" disabled={isSaving}>
              {isSaving ? 'Saving...' : 'Save Task'}
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
      {isLoading && <p role="status">Loading follow-up tasks...</p>}
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
      {!isLoading && !loadError && tasks.length === 0 && (
        <p>No follow-up tasks recorded yet.</p>
      )}
      {!isLoading && !loadError && orderedTasks.length > 0 && (
        <ul className="follow-up-task-list">
          {orderedTasks.map((task) => (
            <li className="follow-up-task-row" key={task.id}>
              <div className="follow-up-task-header">
                <strong>{task.title}</strong>
                <span className="follow-up-task-status">
                  {task.status === 'open' ? 'Open' : task.status === 'completed' ? 'Completed' : 'Cancelled'}
                </span>
              </div>
              <p className="follow-up-task-meta">
                Added <time dateTime={task.created_at}>{task.created_at.slice(0, 10)}</time>
                {task.due_date && (
                  <>{' · '}Due <time dateTime={task.due_date}>{task.due_date}</time></>
                )}
                {task.completed_at && (
                  <>{' · '}Completed <time dateTime={task.completed_at}>
                    {task.completed_at.slice(0, 10)}
                  </time></>
                )}
                {task.cancelled_at && (
                  <>{' · '}Cancelled <time dateTime={task.cancelled_at}>
                    {task.cancelled_at.slice(0, 10)}
                  </time></>
                )}
              </p>
              {task.care_goal_id !== null && (
                <p className="follow-up-task-details">
                  Care goal:{' '}
                  {goals?.find((goal) => goal.id === task.care_goal_id)?.title
                    ?? 'Goal #' + task.care_goal_id}
                  {goals?.find((goal) => goal.id === task.care_goal_id)?.status === 'completed'
                    && ' (completed)'}
                  {goals?.find((goal) => goal.id === task.care_goal_id)?.status === 'discontinued'
                    && ' (discontinued)'}
                </p>
              )}
              {task.details && <p className="follow-up-task-details">{task.details}</p>}
              {task.completion_note && (
                <p className="follow-up-task-details">Outcome: {task.completion_note}</p>
              )}
              {task.cancellation_reason && (
                <p className="follow-up-task-details">Cancellation reason: {task.cancellation_reason}</p>
              )}
              {task.status === 'open' && completingId !== task.id && cancellingId !== task.id && (
                <button
                  className="secondary-action-button follow-up-task-complete-button"
                  type="button"
                  disabled={isSaving}
                  aria-label={'Complete task: ' + task.title}
                  onClick={() => {
                    setShowAddForm(false)
                    setCompletingId(task.id)
                    setCompletionNote('')
                    setCancellingId(null)
                    setCancellationReason('')
                    setActionError(null)
                  }}
                >
                  Mark Complete
                </button>
              )}
              {task.status === 'open' && completingId !== task.id && cancellingId !== task.id && (
                <button
                  className="secondary-action-button follow-up-task-complete-button"
                  type="button"
                  disabled={isSaving}
                  aria-label={'Cancel task: ' + task.title}
                  onClick={() => {
                    setShowAddForm(false)
                    setCompletingId(null)
                    setCompletionNote('')
                    setCancellingId(task.id)
                    setCancellationReason('')
                    setActionError(null)
                  }}
                >
                  Cancel Task
                </button>
              )}
              {task.status === 'open' && cancellingId === task.id && (
                <form
                  className="follow-up-task-form"
                  onSubmit={(event) => void cancelTask(event, task.id)}
                >
                  <label className="form-field">
                    <span>Reason for cancellation *</span>
                    <textarea
                      required
                      maxLength={2000}
                      rows={3}
                      value={cancellationReason}
                      onChange={(event) => setCancellationReason(event.target.value)}
                      placeholder="Explain why this follow-up is no longer needed."
                    />
                  </label>
                  <div className="follow-up-task-actions">
                    <button className="save-patient-button" type="submit" disabled={isSaving}>
                      {isSaving ? 'Saving...' : 'Cancel Task'}
                    </button>
                    <button
                      className="secondary-action-button"
                      type="button"
                      disabled={isSaving}
                      onClick={() => {
                        setCancellingId(null)
                        setCancellationReason('')
                        setActionError(null)
                      }}
                    >
                      Keep Task
                    </button>
                  </div>
                </form>
              )}
              {task.status === 'open' && completingId === task.id && (
                <form
                  className="follow-up-task-form"
                  onSubmit={(event) => void completeTask(event, task.id)}
                >
                  <label className="form-field">
                    <span>Completion note *</span>
                    <textarea
                      required
                      maxLength={2000}
                      rows={3}
                      value={completionNote}
                      onChange={(event) => setCompletionNote(event.target.value)}
                      placeholder="Describe the action taken and outcome."
                    />
                  </label>
                  <div className="follow-up-task-actions">
                    <button className="save-patient-button" type="submit" disabled={isSaving}>
                      {isSaving ? 'Saving...' : 'Complete Task'}
                    </button>
                    <button
                      className="secondary-action-button"
                      type="button"
                      disabled={isSaving}
                      onClick={() => {
                        setCompletingId(null)
                        setCompletionNote('')
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

export default FollowUpTasks
