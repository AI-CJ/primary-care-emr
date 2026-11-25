import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import { localDate } from '../date'
import type { LabOrder, LabResult } from '../types'

export type LabResolution =
  | { kind: 'cancelled'; order: LabOrder }
  | { kind: 'resulted'; result: LabResult }

type Mode = 'result' | 'cancel'

type Props = {
  order: LabOrder
  visitDate: string
  patientName?: string
  active: boolean
  disabled: boolean
  onBegin: () => void
  onDismiss: () => void
  onResolved: (resolution: LabResolution) => void
}

export default function PendingLabActions({ order, visitDate, patientName, active, disabled, onBegin, onDismiss, onResolved }: Props) {
  const [mode, setMode] = useState<Mode>('result')
  const [reason, setReason] = useState('')
  const [collectedOn, setCollectedOn] = useState('')
  const [resultText, setResultText] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const textarea = useRef<HTMLTextAreaElement>(null)
  const buttons = useRef<HTMLDivElement>(null)
  const inFlight = useRef(false)
  const heading = useId()
  const today = localDate()

  useEffect(() => {
    if (!active) return
    if (mode === 'result') input.current?.focus()
    else textarea.current?.focus()
  }, [active, mode])

  function open(next: Mode) {
    setMode(next)
    setError('')
    setReviewed(false)
    setReason('')
    setCollectedOn('')
    setResultText('')
    onBegin()
  }

  function dismiss() {
    if (inFlight.current) return
    onDismiss()
    requestAnimationFrame(() => buttons.current?.querySelector('button')?.focus())
  }

  const valid = mode === 'cancel'
    ? Boolean(reason.trim())
    : Boolean(collectedOn && collectedOn >= visitDate && collectedOn <= today && resultText.trim() && reviewed)

  async function resolve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (inFlight.current || !valid || order.status !== 'ordered') return
    inFlight.current = true
    setBusy(true)
    setError('')
    try {
      const response = await apiFetch(API_BASE_URL + '/lab-orders/' + order.id + (mode === 'cancel' ? '/cancel' : '/result'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mode === 'cancel' ? { reason: reason.trim() }
          : { collected_on: collectedOn, result_text: resultText.trim() }),
      })
      if (!response.ok) throw new Error(await getApiErrorMessage(response))
      if (mode === 'cancel') {
        const saved: LabOrder = await response.json()
        if (saved.id !== order.id || saved.status !== 'cancelled') throw new Error('Unexpected order response. Refresh the worklist before retrying.')
        onResolved({ kind: 'cancelled', order: saved })
      } else {
        const saved: LabResult = await response.json()
        if (saved.lab_order_id !== order.id) throw new Error('Unexpected result response. Refresh the worklist before retrying.')
        onResolved({ kind: 'resulted', result: saved })
      }
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The request could not be updated.')
    } finally {
      inFlight.current = false
      setBusy(false)
    }
  }

  if (order.status !== 'ordered') return null
  if (!active) return <div className="lab-resolution-actions" ref={buttons}>
    <button className="secondary-action-button" type="button" disabled={disabled} onClick={() => open('result')}>Record result</button>
    <button className="secondary-action-button lab-cancel-action" type="button" disabled={disabled} onClick={() => open('cancel')}>Cancel request</button>
  </div>

  return <form className="lab-resolution-form" aria-labelledby={heading} onSubmit={resolve}>
    <h3 id={heading}>{mode === 'cancel' ? 'Cancel lab request' : 'Record lab result'}</h3>
    <p className="lab-resolution-context"><strong>{order.test_name}</strong>{patientName && ' · ' + patientName} · Request #{order.id}</p>
    {mode === 'cancel' ? <>
      <p className="encounter-help">Cancel only if the request is no longer needed or was entered in error. The request, date and reason will remain in the chart. Cancellation cannot be undone.</p>
      <label className="form-field"><span>Cancellation reason *</span><textarea ref={textarea} value={reason}
        onChange={event => setReason(event.target.value)} rows={3} maxLength={1000} required disabled={busy} /></label>
    </> : <>
      <p className="encounter-help">Enter a result that has actually been received. Saving removes this request from the pending queue, but does not release the result to the patient. Saved results cannot be edited.</p>
      <label className="form-field"><span>Collection date *</span><input ref={input} type="date" value={collectedOn}
        min={visitDate} max={today} required disabled={busy} onChange={event => setCollectedOn(event.target.value)} /></label>
      <label className="form-field"><span>Result details *</span><textarea value={resultText} rows={4} maxLength={4000}
        required disabled={busy} onChange={event => { setResultText(event.target.value); setReviewed(false) }} /></label>
      <label className="lab-resolution-review"><input type="checkbox" checked={reviewed} disabled={busy}
        onChange={event => setReviewed(event.target.checked)} /> I verified the result and patient before recording.</label>
    </>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="lab-resolution-actions">
      <button className={mode === 'cancel' ? 'secondary-action-button lab-cancel-action' : 'save-patient-button'}
        type="submit" disabled={busy || !valid}>{busy ? 'Saving…' : mode === 'cancel' ? 'Confirm cancellation' : 'Save result'}</button>
      <button className="secondary-action-button" type="button" disabled={busy} onClick={dismiss}>Keep request pending</button>
    </div>
  </form>
}
