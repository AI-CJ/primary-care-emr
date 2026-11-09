import type { CareGoal } from '../types'

type PortalCareGoalsProps = {
  goals: CareGoal[]
}

function closedOn(goal: CareGoal): string {
  return goal.completed_at || goal.discontinued_at || goal.created_at
}

function PortalCareGoals({ goals }: PortalCareGoalsProps) {
  const activeGoals = goals
    .filter((goal) => goal.status === 'active')
    .sort((first, second) => {
      if (!first.target_date) return second.target_date ? 1 : first.id - second.id
      if (!second.target_date) return -1
      return first.target_date.localeCompare(second.target_date) || first.id - second.id
    })

  const pastGoals = goals
    .filter((goal) => goal.status !== 'active')
    .sort((first, second) =>
      closedOn(second).localeCompare(closedOn(first)) || second.id - first.id)

  return (
    <section className="portal-card" aria-labelledby="portal-goals">
      <h2 id="portal-goals">My care goals</h2>
      <p className="portal-help">
        Goals recorded in your chart, including goals that have ended.
      </p>

      {activeGoals.length === 0 && (
        <p>{pastGoals.length > 0
          ? 'No care goals are currently active.'
          : 'No care goals are listed in your chart.'}</p>
      )}
      {activeGoals.length > 0 && (
        <div className="portal-goal-group">
          <h3>In progress</h3>
          <ul className="portal-records">
            {activeGoals.map((goal) => (
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
      {pastGoals.length > 0 && (
        <div className="portal-goal-group">
          <h3>Past goals</h3>
          <ul className="portal-records">
            {pastGoals.map((goal) => {
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
    </section>
  )
}

export default PortalCareGoals
