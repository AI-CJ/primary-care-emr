import { useEffect, useId, useState } from 'react'
import { apiFetch, API_BASE_URL } from '../api'
import { localDate } from '../date'
import { groupPortalAppointments, formatPortalAppointment } from '../portalAppointments'
import type { PortalAppointmentSummary } from '../types'
import type { PortalSection } from '../portalNavigation'
import { WorkspaceIcon, type WorkspaceIconName } from './WorkspaceIcon'

type AppointmentState = { status: 'loading' | 'error' } | { status: 'ready'; next: PortalAppointmentSummary | undefined }
const actions: { section: PortalSection; title: string; description: string; icon: WorkspaceIconName }[] = [
  { section: 'health', title: 'My health', description: 'Medications, conditions, allergies and vital signs', icon: 'health' },
  { section: 'immunizations', title: 'Vaccinations', description: 'Review your recorded vaccines and dates', icon: 'audit' },
  { section: 'visits', title: 'Appointments & visits', description: 'Review appointments and visit instructions', icon: 'calendar' },
  { section: 'results', title: 'Test results & referrals', description: 'See released results and referral information', icon: 'results' },
  { section: 'care', title: 'Care plan', description: 'Review your health goals and progress', icon: 'heart' },
  { section: 'preferences', title: 'Settings', description: 'Choose how you receive clinic updates', icon: 'settings' },
]

export default function PortalHome({ onNavigate, patientId, active = true }: { onNavigate: (section: PortalSection) => void; patientId?: number; active?: boolean }) {
  const taskId = useId()
  const [result, setResult] = useState<AppointmentState>({ status: 'loading' })
  const [refresh, setRefresh] = useState(0)
  useEffect(() => {
    if (!active) return
    const controller = new AbortController()
    async function load() {
      setResult({ status: 'loading' })
      try {
        const path = patientId === undefined ? '/portal/appointments' : '/patients/' + patientId + '/portal-preview/appointments'
        const response = await apiFetch(API_BASE_URL + path, { signal: controller.signal })
        if (!response.ok) throw new Error('Appointments unavailable')
        const records: PortalAppointmentSummary[] = await response.json()
        const next = groupPortalAppointments(records, localDate()).upcoming[0]
        if (!controller.signal.aborted) setResult({ status: 'ready', next })
      } catch {
        if (!controller.signal.aborted) setResult({ status: 'error' })
      }
    }
    void load()
    return () => controller.abort()
  }, [patientId, active, refresh])

  const next = result.status === 'ready' ? result.next : undefined
  const dateLabel = next ? formatPortalAppointment(next) : ''

  return <div className="portal-home">
    <section className="portal-next-visit" aria-labelledby="portal-next-visit-title">
      <div><p className="portal-next-label"><WorkspaceIcon name="calendar" size={24} /> Upcoming care</p><h2 id="portal-next-visit-title">Your next appointment</h2>
        {result.status === 'loading' && <p role="status">Loading appointments…</p>}
        {result.status === 'error' && <><p role="alert">We couldn't load your appointments.</p><button type="button" onClick={() => setRefresh(n => n + 1)}>Try again</button></>}
        {result.status === 'ready' && (next ? <><p className="next-visit-date"><time dateTime={next.scheduled_date + 'T' + next.start_time}>{dateLabel}</time></p><p>{next.reason_for_visit}{next.status === 'checked_in' ? ' · Checked in' : ''}</p></> : <p>No upcoming appointments are listed.</p>)}
      </div>
      <button className="next-visit-action" type="button" onClick={() => onNavigate('visits')}>View appointments <span aria-hidden="true">→</span></button>
    </section>
    <h2 className="portal-home-heading">Your health at a glance</h2>
    <nav className="portal-task-grid" aria-label={patientId === undefined ? 'Patient portal sections' : 'Patient portal preview sections'}>{actions.filter(action => patientId === undefined || action.section !== 'preferences').map(action =>
      <button className="portal-task" type="button" key={action.section}
        aria-labelledby={taskId + action.section + "-title"} aria-describedby={taskId + action.section + "-description"}
        onClick={() => onNavigate(action.section)}>
        <span className="portal-task-icon"><WorkspaceIcon name={action.icon} size={26} /></span>
        <span><strong id={taskId + action.section + "-title"}>{action.title}</strong><small id={taskId + action.section + "-description"}>{action.description}</small></span><span className="portal-task-arrow" aria-hidden="true">›</span>
      </button>)}</nav>
  </div>
}
