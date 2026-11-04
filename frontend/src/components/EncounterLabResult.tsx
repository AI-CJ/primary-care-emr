import { useEffect, useState, type FormEvent, type ChangeEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { LabOrder, LabResult } from '../types'

type EncounterLabResultProps = {
  order: LabOrder
  visitDate: string
  onRecorded: (orderId: number) => void
}

function EncounterLabResult({ order, visitDate, onRecorded }: EncounterLabResultProps) {
  const [result, setResult] = useState<LabResult | null>(null)
  const [isLoading, setIsLoading] = useState(order.status === 'resulted')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isEntering, setIsEntering] = useState(false)
  const [collectedOn, setCollectedOn] = useState('')
  const [resultText, setResultText] = useState('')
  const [justRecorded, setJustRecorded] = useState(false)
  const now = new Date()
  const latestCollectionDate = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
  ].join('-')

  useEffect(() => {
    if (order.status !== 'resulted') return

    const controller = new AbortController()
    async function loadResult() {
      setIsLoading(true)
      setLoadError(null)
      try {
        const response = await fetch(
          API_BASE_URL + '/lab-orders/' + order.id + '/result',
          { signal: controller.signal }
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const saved: LabResult = await response.json()
        if (!controller.signal.aborted) setResult(saved)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setLoadError(requestError instanceof Error
            ? requestError.message
            : 'The lab result could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadResult()
    return () => controller.abort()
  }, [order.id, order.status])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSaving || !collectedOn || collectedOn < visitDate || collectedOn > latestCollectionDate || !resultText.trim()) return
    if (!window.confirm('Record this lab result? It cannot be edited afterward.')) return

    setIsSaving(true)
    setActionError(null)
    try {
      const response = await fetch(
        API_BASE_URL + '/lab-orders/' + order.id + '/result',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            collected_on: collectedOn,
            result_text: resultText.trim(),
          }),
        }
      )
      if (!response.ok) {
        setActionError(await getApiErrorMessage(response))
        return
      }
      const saved: LabResult = await response.json()
      setResult(saved)
      setJustRecorded(true)
      setIsEntering(false)
      onRecorded(order.id)
    } catch (requestError) {
      console.error(requestError)
      setActionError('The lab result could not be recorded.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section className="encounter-lab-result" aria-label={'Result for ' + order.test_name + ' request ' + order.id}>
      {order.status === 'resulted' ? (
        <>
          {isLoading && <p role="status">Loading lab result...</p>}
          {loadError && <p className="form-error" role="alert">{loadError}</p>}
          {!isLoading && result && (
            <>
              <h4>Result</h4>
              {justRecorded && <p role="status">Lab result recorded.</p>}
              <p className="encounter-meta">
                Collected <time dateTime={result.collected_on}>{result.collected_on}</time>
                {' · Recorded '}
                <time dateTime={result.reported_at}>
                  {result.reported_at.slice(0, 16).replace('T', ' ')}
                </time>
              </p>
              <p className="encounter-lab-reason">{result.result_text}</p>
            </>
          )}
        </>
      ) : (
        <>
          {!isEntering ? (
            <button className="secondary-action-button" type="button" onClick={() => setIsEntering(true)}>
              Record Result
            </button>
          ) : (
            <form className="encounter-lab-form" onSubmit={(event: FormEvent<HTMLFormElement>) => void handleSubmit(event)}>
              <label className="form-field">
                <span>Collection date *</span>
                <input
                  type="date"
                  value={collectedOn}
                  min={visitDate}
                  max={latestCollectionDate}
                  required
                  disabled={isSaving}
                  onChange={(event: ChangeEvent<HTMLInputElement>) => setCollectedOn(event.target.value)}
                />
              </label>
              <label className="form-field">
                <span>Result details *</span>
                <textarea
                  value={resultText}
                  maxLength={4000}
                  rows={3}
                  required
                  disabled={isSaving}
                  onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setResultText(event.target.value)}
                />
              </label>
              <p className="encounter-help">Use fictional findings only. Saved results cannot be edited.</p>
              <div className="encounter-form-actions">
                <button className="secondary-action-button" type="submit" disabled={isSaving || !collectedOn || !resultText.trim()}>
                  {isSaving ? 'Recording...' : 'Save Result'}
                </button>
                <button className="secondary-action-button" type="button" disabled={isSaving} onClick={() => { setIsEntering(false); setActionError(null) }}>
                  Cancel
                </button>
              </div>
            </form>
          )}
          {actionError && <p className="form-error" role="alert">{actionError}</p>}
        </>
      )}
    </section>
  )
}

export default EncounterLabResult
