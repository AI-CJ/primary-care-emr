import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { FollowUpTask } from '../types'
import './GoalFollowUps.css'

type GoalFollowUpsProps = {
  patientId: number
  goalId: number
  goalTitle: string
}

function GoalFollowUps({ patientId, goalId, goalTitle }: GoalFollowUpsProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [tasks, setTasks] = useState<FollowUpTask[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)
  const panelId = 'goal-follow-ups-' + goalId

  useEffect(() => {
    if (!isOpen) return

    const controller = new AbortController()
    setTasks(null)
    setLoadError(null)

    async function loadTasks() {
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
              : 'Linked follow-up tasks could not be loaded.'
          )
        }
      }
    }

    void loadTasks()
    return () => controller.abort()
  }, [patientId, goalId, isOpen, refreshCount])

  const linkedTasks = tasks?.filter((task) => task.care_goal_id === goalId) ?? []

  return (
    <div className="goal-follow-ups">
      <button
        className="secondary-action-button"
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        aria-label={(isOpen ? 'Hide' : 'View') + ' follow-ups for ' + goalTitle}
        onClick={() => setIsOpen((open) => !open)}
      >
        {isOpen ? 'Hide Follow-ups' : 'View Follow-ups'}
      </button>
      {isOpen && (
        <div className="goal-follow-ups-panel" id={panelId}>
          <h3>Follow-ups for {goalTitle}</h3>
          {tasks === null && !loadError && <p role="status">Loading follow-ups...</p>}
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
          {tasks && linkedTasks.length === 0 && (
            <p>No follow-up tasks are linked to this goal.</p>
          )}
          {tasks && linkedTasks.length > 0 && (
            <ul className="goal-follow-ups-list">
              {linkedTasks.map((task) => (
                <li className="goal-follow-ups-row" key={task.id}>
                  <div className="goal-follow-ups-row-header">
                    <strong>{task.title}</strong>
                    <span className="goal-follow-ups-status">
                      {task.status === 'open' ? 'Open' : task.status === 'completed' ? 'Completed' : 'Cancelled'}
                    </span>
                  </div>
                  <p className="goal-follow-ups-meta">
                    Added <time dateTime={task.created_at}>
                      {task.created_at.slice(0, 10)}
                    </time>
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
                  {task.details && <p className="goal-follow-ups-notes">{task.details}</p>}
                  {task.completion_note && (
                    <p className="goal-follow-ups-notes">Outcome: {task.completion_note}</p>
                  )}
                  {task.cancellation_reason && (
                    <p className="goal-follow-ups-notes">Cancellation reason: {task.cancellation_reason}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
          <p className="goal-follow-ups-hint">
            Manage these items in the Follow-up Tasks section of the patient chart.
          </p>
        </div>
      )}
    </div>
  )
}

export default GoalFollowUps
