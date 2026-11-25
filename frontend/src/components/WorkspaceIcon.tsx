import type { ReactNode } from 'react'

export type WorkspaceIconName = 'dashboard' | 'patients' | 'calendar' | 'history' | 'requests' | 'labs' | 'results' | 'referrals' | 'goals' | 'followups' | 'audit' | 'clinician' | 'person' | 'health' | 'heart' | 'settings' | 'arrow'

/** Small, purpose-built line drawings; the visible labels carry the meaning. */
export function WorkspaceIcon({ name, size = 20 }: { name: WorkspaceIconName; size?: number }) {
  const shapes: Record<WorkspaceIconName, ReactNode> = {
    dashboard: <><rect x="3" y="3" width="7" height="7" rx="1.4" /><rect x="14" y="3" width="7" height="7" rx="1.4" /><rect x="3" y="14" width="7" height="7" rx="1.4" /><rect x="14" y="14" width="7" height="7" rx="1.4" /></>,
    patients: <><circle cx="9" cy="7" r="3" /><path d="M3 20v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6m2 3a5 5 0 0 1 3 5v2" /></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2.5" /><path d="M7 3v4m10-4v4M3 10h18m-13 5h3m3 0h2" /></>,
    history: <><path d="M4 8a9 9 0 1 1-1 7M4 3v5h5M12 7v5l4 2" /></>,
    requests: <><rect x="3" y="5" width="18" height="15" rx="2.5" /><path d="M7 3v4m10-4v4M3 10h18M7 15h10m-3-3 3 3-3 3" /></>,
    labs: <><path d="M9 3h6m-5 0v7l-5 8a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-8V3M8 14h8" /></>,
    results: <><path d="M5 3h10l4 4v14H5zM15 3v5h4M8 14l2 2 5-5" /></>,
    referrals: <><path d="M3 12h12m-4-4 4 4-4 4M14 4h7v16h-7" /></>,
    goals: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><path d="M12 12l7-7" /><circle cx="12" cy="12" r=".7" fill="currentColor" /></>,
    followups: <><rect x="5" y="5" width="14" height="16" rx="2" /><path d="M9 5V3h6v2M8 12l2 2 5-5M8 17h8" /></>,
    audit: <><path d="M12 3l8 3v6c0 4-3 7-8 9-5-2-8-5-8-9V6l8-3zM8 12l3 3 5-6" /></>,
    clinician: <><path d="M5 3v6a5 5 0 0 0 10 0V3M3 3h4m6 0h4M10 14v2a5 5 0 0 0 10 0v-2" /><circle cx="20" cy="11" r="2.5" /></>,
    person: <><circle cx="12" cy="8" r="4" /><path d="M4 21v-2a8 8 0 0 1 16 0v2" /></>,
    health: <><rect x="4" y="3" width="16" height="18" rx="3" /><path d="M8 12h8m-4-4v8" /></>,
    heart: <path d="M12 20 4.6 12.5C-1 6.8 7 1 12 7c5-6 13-.2 7.4 5.5Z" />,
    settings: <><path d="M3 6h18M3 12h18M3 18h18" /><circle cx="8" cy="6" r="2" fill="var(--surface, white)" /><circle cx="16" cy="12" r="2" fill="var(--surface, white)" /><circle cx="10" cy="18" r="2" fill="var(--surface, white)" /></>,
    arrow: <path d="M9 5l7 7-7 7" />,
  }
  return <svg className="workspace-icon" width={size} height={size} viewBox="0 0 24 24"
    fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round"
    strokeLinejoin="round" aria-hidden="true" focusable="false">{shapes[name]}</svg>
}
