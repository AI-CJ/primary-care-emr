import { useEffect, useId, useState, type FormEvent } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import { localDate } from '../date'
import { formatPortalDate } from '../portalAppointments'
import ReferencePicker, { type ReferenceChoice } from './ReferencePicker'

type Source = 'clinic' | 'historical_record' | 'patient_reported'
type RecordItem = {
  id: number; patient_id?: number; cvx_code: string; vaccine_name: string; cvx_release?: string
  administered_on: string; source: Source; manufacturer_name: string | null
  manufacturer_code?: string | null; mvx_release?: string | null; lot_number: string | null
  dose_number: number | null; route: string | null; site: string | null
  notes?: string | null; voided_at?: string | null; void_reason?: string | null
}

const sourceLabels: Record<Source, string> = {
  clinic: 'Administered at this clinic',
  historical_record: 'Historical vaccination record',
  patient_reported: 'Patient-reported history',
}

type LoadState = { path: string; status: 'loading' | 'error'; message?: string }
  | { path: string; status: 'ready'; rows: RecordItem[] }

function ImmunizationForm({ patientId, onSaved, onCancel }: { patientId: number; onSaved: () => void; onCancel: () => void }) {
  const [name, setName] = useState('')
  const [vaccine, setVaccine] = useState<ReferenceChoice | null>(null)
  const [manufacturerName, setManufacturerName] = useState('')
  const [manufacturer, setManufacturer] = useState<ReferenceChoice | null>(null)
  const [source, setSource] = useState<Source>('historical_record')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const available = vaccine && (source !== 'clinic' || vaccine.kind === 'Active')
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!available || busy || (manufacturerName.trim() && !manufacturer)) return
    setBusy(true)
    setError('')
    const form = new FormData(event.currentTarget)
    const value = (key: string) => String(form.get(key) ?? '').trim() || null
    try {
      const response = await apiFetch(API_BASE_URL + '/patients/' + patientId + '/immunizations', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cvx_code: vaccine.code, source, administered_on: value('date'),
          manufacturer_code: manufacturer?.code ?? null, lot_number: value('lot'),
          dose_number: value('dose') ? Number(value('dose')) : null,
          route: value('route'), site: value('site'), notes: value('notes') }),
      })
      if (!response.ok) throw new Error(await getApiErrorMessage(response))
      onSaved()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Immunization could not be saved.')
    } finally { setBusy(false) }
  }
  return <form className="immunization-form" onSubmit={save}>
    <p className="encounter-meta">Record a vaccination that has occurred. Do not use this form to order or recommend a vaccine.</p>
    <div className="form-grid">
      <ReferencePicker kind="cvx" label="Vaccine *" value={name} selected={vaccine} required disabled={busy}
        onChange={value => { setName(value); setVaccine(null) }} onSelect={choice => { setName(choice.name); setVaccine(choice) }} />
      <label className="form-field"><span>Date administered *</span><input name="date" type="date" max={localDate()} required disabled={busy} /></label>
      <label className="form-field"><span>Record source *</span><select value={source} disabled={busy} onChange={e => setSource(e.target.value as Source)}>
        {Object.entries(sourceLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      {vaccine && !available && <p role="alert">This code is not an active clinic administration code. Select a historical source only if it describes the recorded event.</p>}
      <ReferencePicker kind="mvx" label="Manufacturer (if documented)" value={manufacturerName} selected={manufacturer} disabled={busy}
        onChange={value => { setManufacturerName(value); setManufacturer(null) }} onSelect={choice => { setManufacturerName(choice.name); setManufacturer(choice) }} />
      <label className="form-field"><span>Lot number</span><input name="lot" maxLength={100} disabled={busy} /></label>
      <label className="form-field"><span>Dose number (if known)</span><input name="dose" type="number" min={1} max={30} step={1} disabled={busy} /></label>
      <label className="form-field"><span>Route</span><select name="route" disabled={busy}><option value="">Not recorded</option>
        <option>Intramuscular</option><option>Subcutaneous</option><option>Intradermal</option><option>Oral</option><option>Intranasal</option><option>Other</option>
      </select></label>
      <label className="form-field"><span>Administration site</span><input name="site" maxLength={80} placeholder="If documented" disabled={busy} /></label>
    </div>
    <label className="form-field"><span>Clinical notes / documentation source</span><textarea name="notes" rows={3} maxLength={2000} disabled={busy} /></label>
    {error && <p role="alert" className="form-error">{error}</p>}
    <div className="problem-form-actions">
      <button type="submit" className="save-patient-button" disabled={busy || !available || Boolean(manufacturerName.trim() && !manufacturer)}>{busy ? 'Saving…' : 'Record vaccination'}</button>
      <button type="button" className="secondary-action-button" onClick={onCancel} disabled={busy}>Cancel</button>
    </div>
  </form>
}

function Correction({ row, onDone, onCancel }: { row: RecordItem; onDone: () => void; onCancel: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    const reason = String(new FormData(event.currentTarget).get('reason') ?? '').trim()
    if (!reason) return
    setBusy(true)
    setError('')
    try {
      const response = await apiFetch(API_BASE_URL + '/immunizations/' + row.id + '/void', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason }),
      })
      if (!response.ok) throw new Error(await getApiErrorMessage(response))
      onDone()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Correction could not be recorded.')
    } finally { setBusy(false) }
  }
  return <form className="immunization-form" onSubmit={save}>
    <p>Marking this record as entered in error retains it in the staff history and removes it from the patient view. A corrected record can then be entered separately.</p>
    <label className="form-field"><span>Correction reason *</span><textarea name="reason" required maxLength={1000} rows={2} disabled={busy} /></label>
    {error && <p role="alert" className="form-error">{error}</p>}
    <div className="problem-form-actions">
      <button className="appointment-cancel-button secondary-action-button" type="submit" disabled={busy}>Confirm entered in error</button>
      <button className="secondary-action-button" type="button" onClick={onCancel} disabled={busy}>Cancel</button>
    </div>
  </form>
}

export default function Immunizations({ patientId, staff = false, archived = false }: { patientId?: number; staff?: boolean; archived?: boolean }) {
  const heading = useId()
  const path = staff ? '/patients/' + patientId + '/immunizations'
    : patientId === undefined ? '/portal/immunizations' : '/patients/' + patientId + '/portal-preview/immunizations'
  const [state, setState] = useState<LoadState>({ path, status: 'loading' })
  const [revision, setRevision] = useState(0)
  const [adding, setAdding] = useState(false)
  const [correcting, setCorrecting] = useState<number | null>(null)
  const [message, setMessage] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      setState({ path, status: 'loading' })
      try {
        const response = await apiFetch(API_BASE_URL + path, { signal: controller.signal })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const rows: RecordItem[] = await response.json()
        if (!Array.isArray(rows) || (staff && rows.some(row => row.patient_id !== patientId))) throw new Error('Unexpected chart records')
        if (!controller.signal.aborted) setState({ path, status: 'ready', rows })
      } catch (reason) {
        if (!controller.signal.aborted) setState({ path, status: 'error',
          message: reason instanceof Error ? reason.message : 'Vaccinations could not be loaded.' })
      }
    }
    void load()
    return () => controller.abort()
  }, [path, revision, staff, patientId])
  const current = state.path === path ? state : { path, status: 'loading' as const }
  const rows = current.status === 'ready' ? current.rows : []
  function finish(text: string) {
    setAdding(false)
    setCorrecting(null)
    setMessage(text)
    setRevision(n => n + 1)
  }
  return <section className={staff ? 'overview-card immunization-card' : 'portal-card immunization-card'} aria-labelledby={heading}>
    <div className={staff ? 'overview-card-header' : 'immunization-heading'}>
      <h2 id={heading}>{staff ? 'Vaccination history' : 'My vaccination history'}</h2>
      {staff && !archived && !adding && correcting === null && <button className="secondary-action-button" type="button"
        onClick={() => { setAdding(true); setMessage('') }}>+ Record vaccination</button>}
    </div>
    <p className={staff ? 'encounter-meta' : 'portal-help'}>This is a record of documented vaccinations, not a determination of which vaccines are due. Missing records do not establish that a vaccine was never received.</p>
    {message && <p role="status" className="portal-confirmation">{message}</p>}
    {adding && patientId !== undefined && <ImmunizationForm patientId={patientId}
      onSaved={() => finish('Vaccination recorded.')} onCancel={() => setAdding(false)} />}
    {current.status === 'loading' && <p role="status">Loading vaccination history…</p>}
    {current.status === 'error' && <><p role="alert">{current.message}</p><button className="secondary-action-button" type="button" onClick={() => setRevision(n => n + 1)}>Try again</button></>}
    {current.status === 'ready' && !rows.length && <p>No vaccinations are recorded in this chart.</p>}
    {current.status === 'ready' && Boolean(rows.length) && <ul className="immunization-list">
      {rows.map(row => <li key={row.id} className={row.voided_at ? 'immunization-voided' : ''}>
        <div className="immunization-row-heading"><strong>{row.vaccine_name}</strong>
          <span className="portal-record-status">{row.voided_at ? 'Entered in error' : sourceLabels[row.source]}</span></div>
        <p><time dateTime={row.administered_on}>{formatPortalDate(row.administered_on)}</time>
          {staff && <> · CVX {row.cvx_code}</>}{row.dose_number && <> · Dose {row.dose_number}</>}</p>
        <dl className="immunization-details">
          <div><dt>Manufacturer</dt><dd>{row.manufacturer_name || 'Not recorded'}</dd></div>
          <div><dt>Lot number</dt><dd>{row.lot_number || 'Not recorded'}</dd></div>
          <div><dt>Route / site</dt><dd>{[row.route, row.site].filter(Boolean).join(' · ') || 'Not recorded'}</dd></div>
        </dl>
        {staff && row.notes && <p>{row.notes}</p>}
        {staff && row.voided_at && <p>Correction: {row.void_reason}</p>}
        {staff && !archived && !row.voided_at && !adding && (correcting === row.id
          ? <Correction row={row} onDone={() => finish('Correction recorded.')} onCancel={() => setCorrecting(null)} />
          : correcting === null && <button className="secondary-action-button" type="button" onClick={() => { setCorrecting(row.id); setMessage('') }}>Mark entered in error</button>)}
      </li>)}
    </ul>}
  </section>
}
