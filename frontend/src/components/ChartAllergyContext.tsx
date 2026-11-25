import { useEffect, useState } from 'react'
import { apiFetch, API_BASE_URL } from '../api'
import type { Allergy } from '../types'

type State = { kind: 'loading' | 'error' } | { kind: 'ready'; records: Allergy[] }

export default function ChartAllergyContext({ patientId, onReview }: { patientId: number; onReview: () => void }) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const response = await apiFetch(API_BASE_URL + '/patients/' + patientId + '/allergies', { signal: controller.signal })
        if (!response.ok) throw new Error('Allergy records unavailable')
        const records: Allergy[] = await response.json()
        if (!Array.isArray(records) || records.some(record => record.patient_id !== patientId)) throw new Error('Unexpected allergy records')
        if (!controller.signal.aborted) setState({ kind: 'ready', records })
      } catch {
        if (!controller.signal.aborted) setState({ kind: 'error' })
      }
    }
    void load()
    return () => controller.abort()
  }, [patientId, revision])

  const active = state.kind === 'ready' ? state.records.filter(record => record.status === 'active') : []
  const historical = state.kind === 'ready' ? state.records.length - active.length : 0
  return <section className={'chart-allergy-context' + (active.length ? ' chart-allergy-recorded' : '')} aria-label="Chart allergy status">
    <div className="chart-allergy-content">
      <h2>Allergy status</h2>
      {state.kind === 'loading' && <p role="status">Checking recorded allergies…</p>}
      {state.kind === 'error' && <p role="alert">Allergy records unavailable. Verify before making clinical decisions.</p>}
      {state.kind === 'ready' && (active.length > 0
        ? <ul>{active.map(record => <li key={record.id}><strong>{record.allergen}</strong> — {record.severity === 'unknown' ? 'Severity unknown' : record.severity + ' severity'}{record.reaction ? '; ' + record.reaction : '; reaction not recorded'}</li>)}</ul>
        : <p>{historical > 0 ? 'No active allergies recorded; historical records exist.' : 'No allergies recorded; allergy status is not established.'}</p>)}
    </div>
    <div className="chart-allergy-actions">
      {state.kind === 'error' && <button type="button" className="secondary-action-button" onClick={() => { setState({ kind: 'loading' }); setRevision(n => n + 1) }}>Retry allergy check</button>}
      <button type="button" className="secondary-action-button" onClick={onReview}>Review health record</button>
    </div>
  </section>
}
