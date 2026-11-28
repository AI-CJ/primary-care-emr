import { useEffect, useState } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import { localDate } from '../date'
import type { StaffDestination } from '../workspaceNavigation'
import type { DailyScheduleEntry } from '../types'
import { WorkspaceIcon } from './WorkspaceIcon'
import { destinationIcon } from '../workspaceIcons'
import { formatPortalDate } from '../portalAppointments'
import { formatWorkQueueCount } from '../workQueueCount'

const queues = [
  { id: 'requests', title: 'Appointment requests', description: 'Review requested changes' },
  { id: 'results', title: 'Results to release', description: 'Review results before release' },
  { id: 'followups', title: 'Open follow-ups', description: 'Review outstanding care tasks' },
  { id: 'labs', title: 'Pending labs', description: 'Track outstanding laboratory orders' },
  { id: 'referrals', title: 'Pending referrals', description: 'Review specialist referrals' },
  { id: 'goals', title: 'Active care goals', description: 'Review ongoing care plans' },
] as const
type QueueId = typeof queues[number]['id']
type LoadState<T> = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: T }

async function loadRows<T>(path: string, signal: AbortSignal): Promise<T[]> {
  const response = await apiFetch(API_BASE_URL + path, { signal })
  if (!response.ok) throw new Error(await getApiErrorMessage(response))
  const data: unknown = await response.json()
  if (!Array.isArray(data)) throw new Error('Unexpected record format.')
  return data as T[]
}

export default function StaffDashboard({ onNavigate }: { onNavigate: (destination: StaffDestination) => void }) {
  const [day, setDay] = useState(localDate)
  const [revision, setRevision] = useState(0)
  const [schedule, setSchedule] = useState<LoadState<DailyScheduleEntry[]>>({ status: 'loading' })
  const [counts, setCounts] = useState<LoadState<Record<QueueId, number>>>({ status: 'loading' })
  useEffect(() => {
    const controller = new AbortController()
    const signal = controller.signal
    async function refreshSchedule() {
      try {
        const data = await loadRows<DailyScheduleEntry>('/schedule?day=' + encodeURIComponent(day), signal)
        if (!signal.aborted) setSchedule({ status: 'ready', data })
      } catch (reason) {
        if (!signal.aborted) setSchedule({ status: 'error', message: reason instanceof Error ? reason.message : 'Could not load schedule.' })
      }
    }
    async function refreshCounts() {
      try {
        const response = await apiFetch(API_BASE_URL + '/worklists/counts', { signal })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const data: unknown = await response.json()
        if (data === null || typeof data !== 'object' || !queues.every(queue => {
          const count = (data as Record<string, unknown>)[queue.id]
          return typeof count === 'number' && Number.isSafeInteger(count) && count >= 0
        })) throw new Error('Unexpected work-queue summary.')
        if (!signal.aborted) setCounts({ status: 'ready', data: data as Record<QueueId, number> })
      } catch (reason) {
        if (!signal.aborted) setCounts({ status: 'error', message: reason instanceof Error ? reason.message : 'Could not load work queues.' })
      }
    }
    void refreshSchedule()
    void refreshCounts()
    return () => controller.abort()
  }, [day, revision])

  function refresh() {
    setSchedule({ status: 'loading' })
    setCounts({ status: 'loading' })
    setDay(localDate())
    setRevision(current => current + 1)
  }
  const entries = schedule.status === 'ready' ? schedule.data : []
  const scheduled = entries.filter(entry => entry.appointment.status === 'scheduled').length
  const checkedIn = entries.filter(entry => entry.appointment.status === 'checked_in').length
  return <main className="staff-dashboard">
    <header className="dashboard-heading">
      <div><p className="workspace-eyebrow">Clinical operations</p><h1>Dashboard</h1><p className="workspace-description">Today's schedule and outstanding work across the clinic.</p></div>
      <button type="button" className="secondary-action-button" onClick={refresh}>Refresh dashboard</button>
    </header>
    <section className="dashboard-schedule" aria-labelledby="dashboard-schedule-title">
      <div><p className="dashboard-kicker"><WorkspaceIcon name="calendar" size={17} /> {formatPortalDate(day)}</p><h2 id="dashboard-schedule-title">Today's schedule</h2>
        {schedule.status === 'loading' && <p role="status">Loading schedule…</p>}
        {schedule.status === 'error' && <p role="alert">Schedule unavailable. {schedule.message}</p>}
        {schedule.status === 'ready' && <dl className="dashboard-metrics">
          <div><dt>Appointments</dt><dd>{entries.length}</dd></div>
          <div><dt>Scheduled</dt><dd>{scheduled}</dd></div>
          <div><dt>Checked in</dt><dd>{checkedIn}</dd></div>
        </dl>}
      </div>
      <div className="dashboard-actions"><button type="button" onClick={() => onNavigate('schedule')}>Open clinic schedule <span aria-hidden="true">→</span></button>
        <button type="button" onClick={() => onNavigate('patients')}>Find a patient <span aria-hidden="true">→</span></button></div>
    </section>
    <h2 className="dashboard-section-title">Work queues</h2>
    <p className="workspace-description">Select a queue to review its records and take action.</p>
    {counts.status === 'error' && <p role="alert">Work-queue counts unavailable. {counts.message} Refresh the dashboard to retry.</p>}
    <div className="dashboard-queue-grid">
      {queues.map(queue => {
        return <button className="dashboard-queue" key={queue.id} type="button" onClick={() => onNavigate(queue.id)}>
          <span className="queue-heading"><span className="queue-icon"><WorkspaceIcon name={destinationIcon(queue.id)} size={22} /></span><span>{queue.title}</span><WorkspaceIcon name="arrow" size={15} /></span>
          <strong className={counts.status === 'ready' ? 'queue-count' : 'queue-count queue-count-unavailable'}>{counts.status === 'ready' ? formatWorkQueueCount(counts.data[queue.id]) : counts.status === 'error' ? 'Unavailable' : 'Loading…'}</strong>
          <span>{counts.status === 'error' ? 'Open queue to review its records' : queue.description}</span>
        </button>
      })}
    </div>
  </main>
}
