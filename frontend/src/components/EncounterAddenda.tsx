import { useEffect, useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { EncounterAddendum } from '../types'

type EncounterAddendaProps = {
  encounterId: number
}

function EncounterAddenda({ encounterId }: EncounterAddendaProps) {
  const [addenda, setAddenda] = useState<EncounterAddendum[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const [content, setContent] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState('')

  useEffect(() => {
    const controller = new AbortController()

    async function loadAddenda() {
      setIsLoading(true)
      setLoadError(null)

      try {
        const response = await fetch(
          API_BASE_URL + '/encounters/' + encounterId + '/addenda',
          { signal: controller.signal }
        )
        if (!response.ok) {
          const message = await getApiErrorMessage(response)
          if (!controller.signal.aborted) setLoadError(message)
          return
        }

        const records: EncounterAddendum[] = await response.json()
        if (!controller.signal.aborted) setAddenda(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setLoadError('Addenda could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadAddenda()
    return () => controller.abort()
  }, [encounterId, retryCount])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = content.trim()
    setSaveError(null)
    setSaveMessage('')

    if (!text) {
      setSaveError('Enter an addendum before saving.')
      return
    }

    setIsSaving(true)
    try {
      const response = await fetch(
        API_BASE_URL + '/encounters/' + encounterId + '/addenda',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: text }),
        }
      )
      if (!response.ok) {
        setSaveError(await getApiErrorMessage(response))
        return
      }

      const saved: EncounterAddendum = await response.json()
      setAddenda((current) => [...current, saved])
      setContent('')
      setSaveMessage('Addendum saved.')
    } catch (requestError) {
      console.error(requestError)
      setSaveError('The addendum could not be saved.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section className="encounter-addenda" aria-labelledby={'addenda-title-' + encounterId}>
      <h3 id={'addenda-title-' + encounterId}>Addenda</h3>
      {isLoading && <p role="status">Loading addenda...</p>}
      {loadError && (
        <div>
          <p className="form-error" role="alert">{loadError}</p>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setRetryCount((count) => count + 1)}
          >
            Retry loading addenda
          </button>
        </div>
      )}
      {!isLoading && !loadError && (
        <>
          {addenda.length === 0 ? (
            <p>No addenda recorded.</p>
          ) : (
            <div className="encounter-addenda-list">
              {addenda.map((entry) => (
                <article className="encounter-addendum" key={entry.id}>
                  <p className="encounter-meta">
                    Added <time dateTime={entry.created_at}>
                      {new Date(entry.created_at).toLocaleString()}
                    </time>
                  </p>
                  <p>{entry.content}</p>
                </article>
              ))}
            </div>
          )}
          <form className="encounter-addenda-form" onSubmit={handleSubmit}>
            <p className="encounter-help">
              Addenda are permanent. They cannot be edited after saving.
            </p>
            <label className="form-field">
              <span>New addendum</span>
              <textarea
                value={content}
                onChange={(event) => {
                  setContent(event.target.value)
                  setSaveMessage('')
                }}
                required
                maxLength={4000}
                rows={3}
                disabled={isSaving}
              />
            </label>
            {saveError && <p className="form-error" role="alert">{saveError}</p>}
            {saveMessage && <p role="status">{saveMessage}</p>}
            <button className="save-patient-button" type="submit" disabled={isSaving}>
              {isSaving ? 'Saving...' : 'Save Addendum'}
            </button>
          </form>
        </>
      )}
    </section>
  )
}

export default EncounterAddenda
