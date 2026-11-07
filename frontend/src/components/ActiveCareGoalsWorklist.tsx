import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { CareGoal } from '../types'

type ActiveCareGoal = CareGoal & {
  patient_name: string
  is_overdue: boolean
}

type ActiveCareGoalsWorklistProps = {
  onBack: () => void
  onOpenPatient: (patientId: number) => void
  patientError: string | null
}

function ActiveCareGoalsWorklist({
  onBack,
  onOpenPatient,
  patientError,
}: ActiveCareGoalsWorklistProps) {
  const [goals, setGoals] = useState<ActiveCareGoal[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setGoals(null)
    setError(null)

    async function loadGoals() {
      try {
        const response = await fetch(
          API_BASE_URL + '/worklists/active-care-goals',
          { signal: controller.signal },
        )
        if (!response.ok) {
          throw new Error(await getApiErrorMessage(response))
        }

        const records: ActiveCareGoal[] = await response.json()
        if (!controller.signal.aborted) setGoals(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(
            requestError instanceof TypeError
              ? 'The server could not be reached. Try again.'
              : requestError instanceof Error
                ? requestError.message
                : 'Active care goals could not be loaded.',
          )
        }
      }
    }

    void loadGoals()
    return () => controller.abort()
  }, [refreshCount])

  return (
    <main className="search-page">
      <section
        className="search-panel schedule-panel"
        aria-labelledby="active-care-goals-heading"
      >
        <button className="back-button" type="button" onClick={onBack}>
          ← Back to patient search
        </button>
        <div className="search-panel-header">
          <div>
            <h1 id="active-care-goals-heading">Active Care Goals</h1>
            <p className="pending-lab-intro">
              Open goals across the clinic, ordered by target date. Overdue goals
              appear first, and goals without target dates appear last. Open a
              chart to review progress or update an outcome.
            </p>
          </div>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setRefreshCount((count) => count + 1)}
            disabled={goals === null && error === null}
          >
            Refresh
          </button>
        </div>

        {patientError && <p className="form-error" role="alert">{patientError}</p>}
        {!goals && !error && (
          <p className="empty-message" role="status">Loading care goals...</p>
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
        {goals && (
          <>
            <p className="schedule-count" role="status">
              {goals.length} active goal{goals.length === 1 ? '' : 's'}
              {goals.some((goal) => goal.is_overdue) && (
                <> {' · '}{goals.filter((goal) => goal.is_overdue).length} overdue</>
              )}
            </p>
            {goals.length === 0 ? (
              <p className="empty-message">No active care goals.</p>
            ) : (
              <ol className="pending-lab-list">
                {goals.map((goal) => (
                  <li className="pending-lab-row" key={goal.id}>
                    <div>
                      <div className="pending-lab-title">
                        <strong>{goal.title}</strong>
                        {goal.is_overdue && (
                          <span className="pending-lab-priority pending-lab-priority-urgent">
                            Overdue
                          </span>
                        )}
                      </div>
                      <p className="pending-lab-meta">
                        {goal.target_date ? (
                          <>Target <time dateTime={goal.target_date}>
                            {goal.target_date}
                          </time></>
                        ) : 'No target date'}
                        {' · '}
                        Added <time dateTime={goal.created_at}>
                          {goal.created_at.slice(0, 10)}
                        </time>
                        {' · '}Goal #{goal.id}
                      </p>
                    </div>
                    <div className="pending-lab-patient">
                      <button
                        className="schedule-patient-link"
                        type="button"
                        onClick={() => onOpenPatient(goal.patient_id)}
                        aria-label={'Open chart for ' + goal.patient_name}
                      >
                        {goal.patient_name}
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
          Synthetic-data demonstration. Care goals are not clinical recommendations.
        </p>
      </section>
    </main>
  )
}

export default ActiveCareGoalsWorklist
