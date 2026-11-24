import { useEffect, useState } from 'react'
import { API_BASE_URL, apiFetch, getApiErrorMessage } from '../api'

type EventType = 'login_success' | 'login_failure' | 'logout' | 'clinical_read' | 'clinical_write' | 'access_denied'
type AuditEvent = {
  id: number
  occurred_at: string
  event_type: EventType
  route_template: string
  http_method: string
  status_code: number
  actor_user_id: number | null
  subject_patient_id: number | null
  resource_id: number | null
}
type Summary = {
  total_events: number
  failed_logins: number
  access_denials: number
  server_errors: number
}
const labels: Record<EventType, string> = {
  login_success: 'Successful sign-in',
  login_failure: 'Failed sign-in',
  logout: 'Sign-out',
  clinical_read: 'Clinical read',
  clinical_write: 'Clinical write',
  access_denied: 'Access denied',
}
const PAGE_SIZE = 50

export default function AuditReview() {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [eventType, setEventType] = useState<EventType | ''>('')
  const [before, setBefore] = useState<number | null>(null)
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const filters = new URLSearchParams({ limit: String(PAGE_SIZE) })
  if (eventType) filters.set('event_type', eventType)
  if (before !== null) filters.set('before_id', String(before))
  const query = filters.toString()

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [page, activity] = await Promise.all([
          apiFetch(API_BASE_URL + '/admin/audit-events?' + query, { signal: controller.signal }),
          apiFetch(API_BASE_URL + '/admin/audit-events/activity?hours=24', { signal: controller.signal }),
        ])
        if (!page.ok) throw new Error(await getApiErrorMessage(page))
        if (!activity.ok) throw new Error(await getApiErrorMessage(activity))
        const rows: AuditEvent[] = await page.json()
        const counts: Summary = await activity.json()
        if (!controller.signal.aborted) {
          setEvents(rows)
          setSummary(counts)
        }
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Audit activity could not be loaded.')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [query, revision])

  async function exportPage() {
    setExporting(true)
    setError(null)
    try {
      const response = await apiFetch(API_BASE_URL + '/admin/audit-events/export?' + query)
      if (!response.ok) throw new Error(await getApiErrorMessage(response))
      const url = URL.createObjectURL(await response.blob())
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'audit-events.csv'
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The audit page could not be exported.')
    } finally {
      setExporting(false)
    }
  }

  return (
    <main className="chart-page">
      <section className="patient-chart">
        <header className="patient-header">
          <div><p className="eyebrow">Administration</p><h1>Audit activity</h1>
            <p>Review access and workflow events. Clinical text and credentials are excluded.</p>
          </div>
        </header>
        <section className="overview-card" aria-labelledby="audit-summary">
          <h2 id="audit-summary">Last 24 hours</h2>
          {summary && <dl className="audit-summary">
            <div><dt>Total events</dt><dd>{summary.total_events}</dd></div>
            <div><dt>Failed sign-ins</dt><dd>{summary.failed_logins}</dd></div>
            <div><dt>Access denials</dt><dd>{summary.access_denials}</dd></div>
            <div><dt>Server errors</dt><dd>{summary.server_errors}</dd></div>
          </dl>}
          <div className="audit-toolbar">
            <label className="form-field">
              <span>Event type</span>
              <select value={eventType} onChange={(event) => {
                setEventType(event.target.value as EventType | '')
                setBefore(null)
              }}>
                <option value="">All events</option>
                {Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <button type="button" className="secondary-action-button" disabled={loading}
              onClick={() => setRevision((value) => value + 1)}>Refresh</button>
            <button type="button" className="secondary-action-button" disabled={loading || exporting || events.length === 0}
              onClick={() => void exportPage()}>{exporting ? 'Exporting…' : 'Export CSV'}</button>
          </div>
          {error && <p role="alert" className="form-error">{error}</p>}
          {loading && <p role="status">Loading audit activity…</p>}
          {!loading && !error && (events.length === 0
            ? <p>No events match the selected filter.</p>
            : <div className="audit-table-scroll" tabIndex={0} role="region" aria-label="Audit event table">
                <table className="audit-table">
                  <thead><tr><th scope="col">Time</th><th scope="col">Event</th><th scope="col">Route</th><th scope="col">Status</th><th scope="col">Actor ID</th><th scope="col">Patient ID</th></tr></thead>
                  <tbody>{events.map((event) => <tr key={event.id}>
                    <td><time dateTime={event.occurred_at}>{new Date(event.occurred_at).toLocaleString()}</time></td>
                    <td>{labels[event.event_type]}</td><td>{event.http_method} {event.route_template}</td>
                    <td>{event.status_code}</td><td>{event.actor_user_id ?? '—'}</td><td>{event.subject_patient_id ?? '—'}</td>
                  </tr>)}</tbody>
                </table>
              </div>)}
          <div className="audit-pagination">
            <button className="secondary-action-button" type="button" disabled={loading || before === null} onClick={() => setBefore(null)}>Latest events</button>
            <button className="secondary-action-button" type="button" disabled={loading || events.length < PAGE_SIZE}
              onClick={() => setBefore(events[events.length - 1].id)}>Older events</button>
          </div>
        </section>
      </section>
    </main>
  )
}
