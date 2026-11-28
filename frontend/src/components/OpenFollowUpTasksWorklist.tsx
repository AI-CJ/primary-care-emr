import { useEffect, useState } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type { FollowUpTask } from '../types'
import { useWorklistView } from '../useWorklistView'
import WorklistControls from './WorklistControls'

type OpenFollowUpTask = FollowUpTask & {
  patient_name: string
  is_overdue: boolean
}

type OpenFollowUpTasksWorklistProps = {
  onBack: () => void
  onOpenPatient: (patientId: number) => void
  patientError: string | null
}

function OpenFollowUpTasksWorklist({
  onBack,
  onOpenPatient,
  patientError,
}: OpenFollowUpTasksWorklistProps) {
  const [tasks, setTasks] = useState<OpenFollowUpTask[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)
  const worklist = useWorklistView(tasks, task =>
    `${task.patient_name} ${task.title} ${task.details ?? ''} ${task.id}`)

  useEffect(() => {
    const controller = new AbortController()
    queueMicrotask(() => {
      if (controller.signal.aborted) return
      setTasks(null)
      setError(null)
    })

    async function loadTasks() {
      try {
        const response = await apiFetch(
          API_BASE_URL + '/worklists/open-follow-up-tasks',
          { signal: controller.signal },
        )
        if (!response.ok) {
          throw new Error(await getApiErrorMessage(response))
        }

        const records: OpenFollowUpTask[] = await response.json()
        if (!controller.signal.aborted) setTasks(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(
            requestError instanceof TypeError
              ? 'The server could not be reached. Try again.'
              : requestError instanceof Error
                ? requestError.message
                : 'Open follow-up tasks could not be loaded.',
          )
        }
      }
    }

    void loadTasks()
    return () => controller.abort()
  }, [refreshCount])

  const overdueCount = tasks?.filter((task) => task.is_overdue).length ?? 0

  return (
    <main className="search-page">
      <section
        className="search-panel schedule-panel"
        aria-labelledby="open-follow-up-tasks-heading"
      >
        <button className="back-button" type="button" onClick={onBack}>
          ← Back to patient search
        </button>
        <div className="search-panel-header">
          <div>
            <h1 id="open-follow-up-tasks-heading">Open Follow-ups</h1>
            <p className="pending-lab-intro">
              Outstanding patient follow-up tasks across the clinic, ordered by
              due date. Overdue tasks appear first, and tasks without due dates
              appear last. Open a chart to record a completion note.
            </p>
          </div>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setRefreshCount((count) => count + 1)}
            disabled={tasks === null && error === null}
          >
            Refresh
          </button>
        </div>

        {patientError && <p className="form-error" role="alert">{patientError}</p>}
        {!tasks && !error && (
          <p className="empty-message" role="status">Loading follow-up tasks...</p>
        )}
        {error && (
          <div>
            <p className="form-error" role="alert">{error}</p>
            <button
              className="secondary-action-button"
              type="button"
              onClick={() => setRefreshCount((count) => count + 1)}
            >
              Try Again
            </button>
          </div>
        )}
        {tasks && (
          <>
            <WorklistControls {...worklist.controls} label="Open follow-ups"
              searchLabel="Find a follow-up" placeholder="Patient, task or task number"
              summary={<>{tasks.length} open task{tasks.length === 1 ? '' : 's'}
                {overdueCount > 0 && <> · {overdueCount} overdue</>}</>} />
            {worklist.rows.length === 0 ? (
              <p className="empty-message">{tasks.length ? 'No follow-up tasks match your search.' : 'No open follow-up tasks.'}</p>
            ) : (
              <ol className="pending-lab-list" start={worklist.controls.start + 1} aria-label="Open follow-up tasks">
                {worklist.rows.map((task) => (
                  <li className="pending-lab-row" key={task.id}>
                    <div>
                      <div className="pending-lab-title">
                        <strong>{task.title}</strong>
                        {task.is_overdue && (
                          <span className="pending-lab-priority pending-lab-priority-urgent">
                            Overdue
                          </span>
                        )}
                      </div>
                      <p className="pending-lab-meta">
                        {task.due_date ? (
                          <>Due <time dateTime={task.due_date}>{task.due_date}</time></>
                        ) : 'No due date'}
                        {' · '}Added <time dateTime={task.created_at}>
                          {task.created_at.slice(0, 10)}
                        </time>
                        {' · '}Task #{task.id}
                      </p>
                      {task.details && (
                        <p className="pending-lab-reason">{task.details}</p>
                      )}
                    </div>
                    <div className="pending-lab-patient">
                      <button
                        className="schedule-patient-link"
                        type="button"
                        onClick={() => onOpenPatient(task.patient_id)}
                        aria-label={'Open chart for ' + task.patient_name}
                      >
                        {task.patient_name}
                      </button>
                      <span>Open patient chart</span>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
        <p className="pending-lab-disclaimer">
          These tasks do not send notifications.
        </p>
      </section>
    </main>
  )
}

export default OpenFollowUpTasksWorklist
