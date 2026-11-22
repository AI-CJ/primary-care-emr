import type { PortalCareGoalSummary } from './types'

// Keep the newest closed goals visible without losing the active target-date order.
export function groupPortalCareGoals(goals: PortalCareGoalSummary[]) {
  const active = goals
    .filter((goal) => goal.status === 'active')
    .sort((first, second) => {
      if (!first.target_date) return second.target_date ? 1 : first.id - second.id
      if (!second.target_date) return -1
      return first.target_date.localeCompare(second.target_date) || first.id - second.id
    })

  const past = goals
    .filter((goal) => goal.status !== 'active')
    .sort((first, second) => {
      const firstClosed = first.completed_at || first.discontinued_at || first.created_at
      const secondClosed = second.completed_at || second.discontinued_at || second.created_at
      return secondClosed.localeCompare(firstClosed) || second.id - first.id
    })

  return { active, past }
}
