import { useEffect, useState } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type { PortalCareGoalSummary } from '../types'
import { groupPortalCareGoals } from '../portalCareGoalGroups'

type PortalCareGoalsProps = {
  // Staff preview supplies chart-scoped data; patient sign-in never sends a chart ID.
  goals?: PortalCareGoalSummary[]
}

function PortalCareGoals({ goals }: PortalCareGoalsProps) {
  const [loaded, setLoaded] = useState<PortalCareGoalSummary[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    if (goals !== undefined) return

    const controller = new AbortController()

    async function loadGoals() {
      setIsLoading(true)
      setError(null)
      setLoaded(null)

      try {
        const response = await apiFetch(API_BASE_URL + '/portal/care-goals', {
          signal: controller.signal,
        })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: PortalCareGoalSummary[] = await response.json()
        if (!controller.signal.aborted) setLoaded(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof TypeError
            ? 'Care goals could not be loaded. Check your connection and try again.'
            : requestError instanceof Error
              ? requestError.message
              : 'Care goals could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadGoals()
    return () => controller.abort()
  }, [goals, refreshCount])

  const showRecords = goals !== undefined || (!isLoading && !error && loaded !== null)
  const { active, past } = groupPortalCareGoals(goals ?? loaded ?? [])

  return (
    <section className="portal-card" aria-labelledby="portal-goals">
      <h2 id="portal-goals">My care goals</h2>
      <p className="portal-help">
        Goals recorded in your chart, including goals that have ended.
      </p>

      {goals === undefined && isLoading && <p role="status">Loading care goals...</p>}
      {goals === undefined && error && (
        <div>
          <p role="alert">{error}</p>
          <button
            type="button"
            className="secondary-action-button"
            onClick={() => setRefreshCount((count) => count + 1)}
          >
            Try Again
          </button>
        </div>
      )}
      {showRecords && (
        <>
          {active.length === 0 && (
            <p>{past.length > 0
              ? 'No care goals are currently active.'
              : 'No care goals are listed in your chart.'}</p>
          )}
          {active.length > 0 && (
            <div className="portal-goal-group">
              <h3>In progress</h3>
              <ul className="portal-records">
                {active.map((goal) => (
                  <li key={goal.id}>
                    <strong>{goal.title}</strong>
                    {goal.target_date && (
                      <span>Target: <time dateTime={goal.target_date}>
                        {goal.target_date}
                      </time></span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {past.length > 0 && (
            <div className="portal-goal-group">
              <h3>Past goals</h3>
              <ul className="portal-records">
                {past.map((goal) => {
                  const closedDate = goal.status === 'completed'
                    ? goal.completed_at : goal.discontinued_at
                  return (
                    <li key={goal.id}>
                      <strong>{goal.title}</strong>
                      <span>
                        {goal.status === 'completed' ? 'Completed' : 'Discontinued'}
                        {closedDate && (
                          <> on <time dateTime={closedDate}>
                            {closedDate.slice(0, 10)}
                          </time></>
                        )}
                      </span>
                    </li>
                  )
                })}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default PortalCareGoals
