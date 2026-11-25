import { useEffect, useState } from 'react'
import { apiFetch, API_BASE_URL } from '../api'
import type { Problem, Medication, Vital } from '../types'
import { latestRecordedVital } from '../chartSummary'
import { formatPortalVitalReadings } from '../portalVitalReadings'

type PatientRecord = { id: number; patient_id: number }
type Load<T> = { status: 'loading' | 'error' } | { status: 'ready'; records: T[] }

function useRecords<T extends PatientRecord>(patientId: number, resource: string) {
  const [state, setState] = useState<Load<T>>({ status: 'loading' })
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const response = await apiFetch(API_BASE_URL + '/patients/' + patientId + '/' + resource, { signal: controller.signal })
        if (!response.ok) throw new Error('Unable to load chart records')
        const records: T[] = await response.json()
        if (!Array.isArray(records) || records.some(record => record.patient_id !== patientId)) throw new Error('Unexpected chart records')
        if (!controller.signal.aborted) setState({ status: 'ready', records })
      } catch {
        if (!controller.signal.aborted) setState({ status: 'error' })
      }
    }
    void load()
    return () => controller.abort()
  }, [patientId, resource, revision])

  return { state, retry: () => { setState({ status: 'loading' }); setRevision(n => n + 1) } }
}

function Unavailable({ retry }: { retry: () => void }) {
  return <><p role="alert">Records unavailable.</p><button className="secondary-action-button" type="button" onClick={retry}>Retry</button></>
}

const limit = 4

export default function ClinicalSnapshot({ patientId, onReview }: { patientId: number; onReview: () => void }) {
  const problems = useRecords<Problem>(patientId, 'problems')
  const medications = useRecords<Medication>(patientId, 'medications')
  const vitals = useRecords<Vital>(patientId, 'vitals')
  const activeProblems = problems.state.status === 'ready' ? problems.state.records.filter(item => item.status === 'active') : []
  const activeMedications = medications.state.status === 'ready' ? medications.state.records.filter(item => item.status === 'active') : []
  const vital = vitals.state.status === 'ready' ? latestRecordedVital(vitals.state.records) : undefined
  const readings = vital ? formatPortalVitalReadings(vital) : []
  return <section className="clinical-snapshot" aria-label="Clinical snapshot">
    <div className="clinical-snapshot-heading"><div><h3>Clinical snapshot</h3><p>Current chart entries and the most recent dated vital record.</p></div><button className="secondary-action-button" type="button" onClick={onReview}>Open full health record</button></div>
    <div className="clinical-snapshot-grid">
      <section className="overview-card snapshot-card" aria-labelledby="snapshot-conditions">
        <h4 id="snapshot-conditions">Active conditions</h4>
        {problems.state.status === 'loading' && <p role="status">Loading conditions…</p>}
        {problems.state.status === 'error' && <Unavailable retry={problems.retry} />}
        {problems.state.status === 'ready' && (activeProblems.length ? <>
          <p className="snapshot-count">{activeProblems.length} active</p>
          <ul>{activeProblems.slice(0, limit).map(item => <li key={item.id}><strong>{item.name}</strong>{item.onset_date && <small>Onset {item.onset_date}</small>}</li>)}</ul>
          {activeProblems.length > limit && <p className="snapshot-overflow">{activeProblems.length - limit} more in the full health record.</p>}
        </> : <p>No active conditions recorded.</p>)}
      </section>
      <section className="overview-card snapshot-card" aria-labelledby="snapshot-medications">
        <h4 id="snapshot-medications">Active medications</h4>
        {medications.state.status === 'loading' && <p role="status">Loading medications…</p>}
        {medications.state.status === 'error' && <Unavailable retry={medications.retry} />}
        {medications.state.status === 'ready' && (activeMedications.length ? <>
          <p className="snapshot-count">{activeMedications.length} active</p>
          <ul>{activeMedications.slice(0, limit).map(item => <li key={item.id}><strong>{[item.name, item.strength].filter(Boolean).join(' ')}</strong><small>{[item.dose, item.route, item.frequency].filter(Boolean).join(' · ') || 'Dose and schedule not recorded'}</small></li>)}</ul>
          {activeMedications.length > limit && <p className="snapshot-overflow">{activeMedications.length - limit} more in the full health record.</p>}
        </> : <p>No active medications recorded.</p>)}
      </section>
      <section className="overview-card snapshot-card" aria-labelledby="snapshot-vitals">
        <h4 id="snapshot-vitals">Latest vital record</h4>
        {vitals.state.status === 'loading' && <p role="status">Loading vital signs…</p>}
        {vitals.state.status === 'error' && <Unavailable retry={vitals.retry} />}
        {vitals.state.status === 'ready' && (vital ? <>
          <p className="snapshot-count">Recorded <time dateTime={vital.recorded_on}>{vital.recorded_on}</time></p>
          {readings.length ? <ul>{readings.map(reading => <li key={reading}>{reading}</li>)}</ul> : <p>No measurements recorded in this entry.</p>}
          <p className="snapshot-overflow">Missing readings are not estimated.</p>
        </> : <p>No vital records available.</p>)}
      </section>
    </div>
  </section>
}
