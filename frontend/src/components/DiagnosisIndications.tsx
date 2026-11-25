import { useEffect, useState } from 'react'
import { API_BASE_URL, apiFetch, getApiErrorMessage } from '../api'
import type { DiagnosisIndication, Problem } from '../types'

export function DiagnosisLabel({ code }: { code?: string | null }) {
  return <span className={code ? 'diagnosis-code' : 'diagnosis-uncoded'}>{code ?? 'Not coded'}</span>
}

export default function DiagnosisIndications({ records, compact = false }: { records?: DiagnosisIndication[]; compact?: boolean }) {
  return <div className={'record-indications' + (compact ? ' record-indications-compact' : '')}>
    <span className="indication-label">Indications</span>
    {records?.length ? <ul>{records.map(record => <li key={record.problem_id}>
      <DiagnosisLabel code={record.icd10_code} /> <span>{record.problem_name}</span>
    </li>)}</ul> : <span className="diagnosis-help">No linked problem recorded.</span>}
  </div>
}

export function DiagnosisIndicationPicker({ patientId, selected, onChange, disabled = false }: {
  patientId: number; selected: number[]; onChange: (ids: number[]) => void; disabled?: boolean
}) {
  const [result, setResult] = useState<{ patientId: number; records: Problem[] } | { patientId: number; error: string } | null>(null)
  const [revision, setRevision] = useState(0)
  const current = result?.patientId === patientId ? result : null
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const response = await apiFetch(API_BASE_URL + '/patients/' + patientId + '/problems', { signal: controller.signal })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const records: Problem[] = await response.json()
        if (records.some(record => record.patient_id !== patientId)) throw new Error('Unexpected chart problems.')
        if (!controller.signal.aborted) setResult({ patientId, records })
      } catch (error) {
        if (!controller.signal.aborted) setResult({ patientId, error: error instanceof Error ? error.message : 'Unable to load chart problems.' })
      }
    }
    void load()
    return () => controller.abort()
  }, [patientId, revision])
  return <fieldset className="indication-picker" disabled={disabled}>
    <legend>Associated chart problems (ICD-10-CM)</legend>
    <p className="diagnosis-help">Select the documented reason or reasons. Leave unselected if no indication is recorded; nothing is assigned automatically.</p>
    {!current && <p role="status">Loading chart problems…</p>}
    {current && 'error' in current && <><p role="alert">{current.error} Existing selections are retained.</p>
      <button type="button" className="secondary-action-button" onClick={() => setRevision(n => n + 1)}>Retry</button></>}
    {current && 'records' in current && (current.records.length ? <div className="indication-options">
      {current.records.map(problem => <label className="indication-option" key={problem.id}>
        <input type="checkbox" checked={selected.includes(problem.id)}
          disabled={selected.length >= 20 && !selected.includes(problem.id)}
          onChange={event => onChange(event.target.checked ? [...selected, problem.id] : selected.filter(id => id !== problem.id))} />
        <span><DiagnosisLabel code={problem.icd10_code} /> {problem.name}<small>{problem.status === 'active' ? 'Active' : 'Resolved'}</small></span>
      </label>)}
    </div> : <p>No chart problems are recorded. Add a problem in the health record first, if applicable.</p>)}
  </fieldset>
}
