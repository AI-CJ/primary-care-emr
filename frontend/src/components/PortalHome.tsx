import { useEffect, useState } from 'react'
import { apiFetch, API_BASE_URL } from '../api'
import { localDate } from '../date'
import { groupPortalAppointments, formatPortalAppointment } from '../portalAppointments'
import type { PortalAppointmentSummary } from '../types'
import type { PortalSection } from '../portalNavigation'

type AppointmentState = { status: 'loading' | 'error' } | { status: 'ready'; next: PortalAppointmentSummary | undefined }
const actions: { section: PortalSection; title: string; description: string; icon: string }[] = [
  { section: 'health', title: 'My health', description: 'Medications, conditions, allergies and vital signs', icon: 'health' },
  { section: 'visits', title: 'Appointments & visits', description: 'Review appointments and visit instructions', icon: 'calendar' },
  { section: 'results', title: 'Test results & referrals', description: 'See released results and referral information', icon: 'results' },
  { section: 'care', title: 'My care plan', description: 'Review your health goals and progress', icon: 'heart' },
  { section: 'preferences', title: 'Communication preferences', description: 'Choose how you receive clinic updates', icon: 'settings' },
]

function TaskIcon({ name }: { name: string }) {
  return <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {name === 'health' ? <><rect x="4" y="3" width="16" height="18" rx="3" /><path d="M8 12h8m-4-4v8" /></>
      : name === 'calendar' ? <><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M7 3v4m10-4v4M3 10h18m-13 5h3m3 0h2" /></>
      : name === 'results' ? <><path d="M5 3h10l4 4v14H5zM15 3v5h4M8 12h8m-8 4h5" /></>
      : name === 'heart' ? <path d="M12 20 4.6 12.5C-1 6.8 7 1 12 7c5-6 13-.2 7.4 5.5Z" />
      : <><path d="M3 6h18M3 12h18M3 18h18" /><circle cx="8" cy="6" r="2" fill="white" /><circle cx="16" cy="12" r="2" fill="white" /><circle cx="10" cy="18" r="2" fill="white" /></>}
  </svg>
}

export default function PortalHome({ onNavigate, patientId, active = true }: { onNavigate: (section: PortalSection) => void; patientId?: number; active?: boolean }) {
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
      <div><p className="portal-next-label"><TaskIcon name="calendar" /> Upcoming care</p><h2 id="portal-next-visit-title">Your next appointment</h2>
        {result.status === 'loading' && <p role="status">Loading appointments…</p>}
        {result.status === 'error' && <><p role="alert">We couldn't load your appointments.</p><button type="button" onClick={() => setRefresh(n => n + 1)}>Try again</button></>}
        {result.status === 'ready' && (next ? <><p className="next-visit-date"><time dateTime={next.scheduled_date + 'T' + next.start_time}>{dateLabel}</time></p><p>{next.reason_for_visit}{next.status === 'checked_in' ? ' · Checked in' : ''}</p></> : <p>No upcoming appointments are listed.</p>)}
      </div>
      <button className="next-visit-action" type="button" onClick={() => onNavigate('visits')}>View appointments <span aria-hidden="true">→</span></button>
    </section>
    <h2 className="portal-home-heading">What would you like to do?</h2>
    <div className="portal-task-grid">{actions.filter(action => patientId === undefined || action.section !== 'preferences').map(action =>
      <button className="portal-task" type="button" key={action.section} onClick={() => onNavigate(action.section)}>
        <span className="portal-task-icon"><TaskIcon name={action.icon} /></span>
        <span><strong>{action.title}</strong><small>{action.description}</small></span><span className="portal-task-arrow" aria-hidden="true">›</span>
      </button>)}</div>
  </div>
}
