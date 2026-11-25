import { useCallback, useEffect, useId, useState } from 'react'
import { apiFetch, API_BASE_URL } from '../api'
import { formatPortalDate } from '../portalAppointments'

type Background = {
  patient_id: number
  reviewed_on: string
  medical_history: string
  surgical_history: string
  family_history: string
  social_history: string
  care_context: string
}

type Imaging = {
  id: number
  patient_id?: number
  performed_on: string
  reported_on: string
  modality: string
  study: string
  indication: string
  findings: string
  impression: string
  source: string
  shared_on?: string | null
}

type Load<T> = { key: string; status: 'ready'; data: T } | { key: string; status: 'error' }

function useHistory<T>(path: string, validate: (data: T) => boolean) {
  const [revision, setRevision] = useState(0)
  const [state, setState] = useState<Load<T> | null>(null)
  const key = path + ':' + revision
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const response = await apiFetch(API_BASE_URL + path, { signal: controller.signal })
        if (!response.ok) throw new Error('History unavailable')
        const data: T = await response.json()
        if (!validate(data)) throw new Error('Unexpected history records')
        if (!controller.signal.aborted) setState({ key, status: 'ready', data })
      } catch {
        if (!controller.signal.aborted) setState({ key, status: 'error' })
      }
    }
    void load()
    return () => controller.abort()
  }, [key, path, validate])
  return { state: state?.key === key ? state : null, retry: () => setRevision(n => n + 1) }
}

function HistoryError({ retry }: { retry: () => void }) {
  return <><p role="alert">History could not be loaded.</p><button className="secondary-action-button" type="button" onClick={retry}>Try again</button></>
}

const labels: [keyof Omit<Background, 'patient_id' | 'reviewed_on'>, string][] = [
  ['medical_history', 'Medical history'],
  ['surgical_history', 'Surgical history'],
  ['family_history', 'Family history'],
  ['social_history', 'Social history'],
  ['care_context', 'Care context & preferences'],
]

export function PatientBackground({ patientId }: { patientId: number }) {
  const heading = useId()
  const validate = useCallback((data: Background | null) =>
    data === null || (data.patient_id === patientId && labels.every(([field]) => typeof data[field] === 'string')), [patientId])
  const { state, retry } = useHistory<Background | null>('/patients/' + patientId + '/background', validate)
  return <section className="overview-card chart-history-card" aria-labelledby={heading}>
    <div className="overview-card-header"><h2 id={heading}>Patient background</h2></div>
    {!state && <p role="status">Loading patient background…</p>}
    {state?.status === 'error' && <HistoryError retry={retry} />}
    {state?.status === 'ready' && (state.data ? <>
      <p className="encounter-meta">Recorded at review on <time dateTime={state.data.reviewed_on}>{formatPortalDate(state.data.reviewed_on)}</time>. Historical context, not a live medication reconciliation.</p>
      <dl className="chart-background-grid">
        {labels.map(([field, label]) => <div key={field}><dt>{label}</dt><dd>{state.data?.[field]}</dd></div>)}
      </dl>
    </> : <p>No background history has been recorded.</p>)}
  </section>
}

function validReports(data: Imaging[]): boolean {
  return Array.isArray(data) && data.every(report =>
    Number.isInteger(report.id) && typeof report.study === 'string' &&
    typeof report.impression === 'string' && typeof report.findings === 'string')
}

export function ImagingHistory({ patientId, staff = false }: { patientId?: number; staff?: boolean }) {
  const heading = useId()
  const path = staff ? '/patients/' + patientId + '/imaging-reports'
    : patientId === undefined ? '/portal/imaging-reports'
      : '/patients/' + patientId + '/portal-preview/imaging-reports'
  const validate = useCallback((data: Imaging[]) => validReports(data) &&
    (!staff || data.every(report => report.patient_id === patientId)), [patientId, staff])
  const { state, retry } = useHistory<Imaging[]>(path, validate)
  return <section className={staff ? 'overview-card chart-history-card' : 'portal-card chart-history-card'} aria-labelledby={heading}>
    <h2 id={heading}>{staff ? 'Prior imaging reports' : 'My shared imaging reports'}</h2>
    <p className={staff ? 'encounter-meta' : 'portal-help'}>
      {staff ? 'Historical report text, with findings and the recorded impression. Image files are not stored here.'
        : 'Read the reports your clinic has shared. Ask your care team about what the findings mean for you.'}
    </p>
    {!state && <p role="status">Loading imaging reports…</p>}
    {state?.status === 'error' && <HistoryError retry={retry} />}
    {state?.status === 'ready' && (state.data.length ? <ul className="chart-imaging-list">
      {state.data.map(report => <li key={report.id}>
        <details>
          <summary>
            <strong>{report.study}</strong>
            <span>{report.modality} · <time dateTime={report.performed_on}>{formatPortalDate(report.performed_on)}</time></span>
          </summary>
          <dl className="chart-report-details">
            <div><dt>Reason for study</dt><dd>{report.indication}</dd></div>
            <div><dt>Findings</dt><dd>{report.findings}</dd></div>
            <div><dt>Impression</dt><dd>{report.impression}</dd></div>
            <div><dt>Report date</dt><dd><time dateTime={report.reported_on}>{formatPortalDate(report.reported_on)}</time></dd></div>
            <div><dt>Source</dt><dd>{report.source}</dd></div>
            {staff && <div><dt>Portal status</dt><dd>{report.shared_on ? 'Shared ' + formatPortalDate(report.shared_on) : 'Not shared'}</dd></div>}
          </dl>
        </details>
      </li>)}
    </ul> : <p>{staff ? 'No prior imaging reports recorded.' : 'No imaging reports have been shared.'}</p>)}
  </section>
}
