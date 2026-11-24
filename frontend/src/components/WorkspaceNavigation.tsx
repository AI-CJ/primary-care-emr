import { type StaffDestination, staffDestinationLabels } from '../workspaceNavigation'

const groups: { label: string; destinations: StaffDestination[] }[] = [
  { label: 'Clinical', destinations: ['patients', 'schedule', 'past'] },
  { label: 'Work queues', destinations: ['requests', 'labs', 'results', 'referrals', 'goals', 'followups'] },
  { label: 'Administration', destinations: ['audit'] },
]

type Props = {
  current: StaffDestination
  isAdmin: boolean
  onNavigate: (destination: StaffDestination) => void
}

export default function WorkspaceNavigation({ current, isAdmin, onNavigate }: Props) {
  const visible = groups.filter((group) => isAdmin || group.label !== 'Administration')
  return (
    <aside className="workspace-sidebar">
      <div className="workspace-sidebar-heading">Workspace</div>
      <nav className="workspace-nav" aria-label="Staff workspace">
        {visible.map((group) => (
          <div className="workspace-nav-group" key={group.label}>
            <p>{group.label}</p>
            {group.destinations.map((destination) => (
              <button key={destination} type="button"
                aria-current={current === destination ? 'page' : undefined}
                onClick={() => onNavigate(destination)}>
                {staffDestinationLabels[destination]}
              </button>
            ))}
          </div>
        ))}
      </nav>
      <label className="workspace-mobile-nav">
        <span>Workspace</span>
        <select aria-label="Staff workspace" value={current}
          onChange={(event) => onNavigate(event.target.value as StaffDestination)}>
          {visible.map((group) => (
            <optgroup key={group.label} label={group.label}>
              {group.destinations.map((destination) => <option key={destination} value={destination}>{staffDestinationLabels[destination]}</option>)}
            </optgroup>
          ))}
        </select>
      </label>
    </aside>
  )
}
