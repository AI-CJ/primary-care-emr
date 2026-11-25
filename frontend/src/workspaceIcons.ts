import type { StaffDestination } from './workspaceNavigation'
import type { WorkspaceIconName } from './components/WorkspaceIcon'

const destinationIcons: Record<StaffDestination, WorkspaceIconName> = {
  dashboard: 'dashboard', patients: 'patients', schedule: 'calendar', past: 'history',
  requests: 'requests', labs: 'labs', results: 'results', referrals: 'referrals',
  goals: 'goals', followups: 'followups', audit: 'audit',
}

export function destinationIcon(destination: StaffDestination): WorkspaceIconName {
  return destinationIcons[destination]
}
