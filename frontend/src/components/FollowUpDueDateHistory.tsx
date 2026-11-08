import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'

type DueDateChange = {
  id: number
  task_id: number
  previous_due_date: string | null
  new_due_date: string | null
  reason: string
  changed_at: string
}

type FollowUpDueDateHistoryProps = {
  taskId: number
  taskTitle: string
  refreshKey: number
}

function FollowUpDueDateHistory({ taskId, taskTitle, refreshKey }: FollowUpDueDateHistoryProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [changes, setChanges] = useState<DueDateChange[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const panelId = 'follow-up-due-date-history-' + taskId

  useEffect(() => {
    if (!isOpen) return

    const controller = new AbortController()
    setChanges(null)
    setLoadError(null)

    async function loadHistory() {
      try {
        const response = await fetch(
          API_BASE_URL + '/follow-up-tasks/' + taskId + '/due-date-changes',
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: DueDateChange[] = await response.json()
        if (!controller.signal.aborted) setChanges(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setLoadError(
            requestError instanceof Error
              ? requestError.message
              : 'Due date history could not be loaded.',
          )
        }
      }
    }

    void loadHistory()
    return () => controller.abort()
  }, [taskId, isOpen, refreshKey, retryCount])

  return (
    <div className="follow-up-due-date-history">
      <button
        className="secondary-action-button"
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        aria-label={(isOpen ? 'Hide' : 'View') + ' due date history for ' + taskTitle}
        onClick={() => setIsOpen((open) => !open)}
      >
        {isOpen ? 'Hide Due Date History' : 'Due Date History'}
      </button>
      {isOpen && (
        <div className="follow-up-due-date-history-panel" id={panelId}>
          <h3>Due date history for {taskTitle}</h3>
          {changes === null && !loadError && (
            <p role="status">Loading due date history...</p>
          )}
          {loadError && (
            <div>
              <p className="form-error" role="alert">{loadError}</p>
              <button
                className="secondary-action-button"
                type="button"
                onClick={() => setRetryCount((count) => count + 1)}
              >
                Try Again
              </button>
            </div>
          )}
          {changes && changes.length === 0 && (
            <p>No due date changes recorded.</p>
          )}
          {changes && changes.length > 0 && (
            <ol className="follow-up-due-date-history-list">
              {changes.map((change) => (
                <li key={change.id}>
                  <p>
                    {change.previous_due_date ?? 'No due date'}
                    {' → '}
                    {change.new_due_date ?? 'No due date'}
                  </p>
                  <p>{change.reason}</p>
                  <time dateTime={change.changed_at}>
                    {new Date(change.changed_at).toLocaleString()}
                  </time>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  )
}

export default FollowUpDueDateHistory
