import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'

type Preferences = {
  preferred_channel: 'portal' | 'phone' | 'email'
  appointment_reminders: boolean
  care_updates: boolean
}

const ENDPOINT = API_BASE_URL + '/portal/communication-preferences'

export default function PortalCommunicationPreferences() {
  const [preferences, setPreferences] = useState<Preferences | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      setLoading(true)
      setError(null)
      setNotice(null)
      try {
        const response = await apiFetch(ENDPOINT, { signal: controller.signal })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const data: Preferences = await response.json()
        if (!controller.signal.aborted) setPreferences(data)
      } catch (reason) {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Unable to load preferences.')
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [refresh])

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!preferences || saving) return
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const response = await apiFetch(ENDPOINT, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      })
      if (!response.ok) throw new Error(await getApiErrorMessage(response))
      const saved: Preferences = await response.json()
      setPreferences(saved)
      setNotice('Your communication preferences were saved.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to save preferences.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="portal-card" aria-labelledby="portal-communication">
      <h2 id="portal-communication">Communication preferences</h2>
      <p className="portal-help">
        Choose how you prefer to receive clinic updates.
        These choices do not send messages or schedule reminders.
      </p>
      {loading && <p role="status">Loading communication preferences...</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !preferences && (
        <button type="button" className="secondary-action-button"
          onClick={() => setRefresh((current) => current + 1)}>
          Try Again
        </button>
      )}
      {!loading && preferences && (
        <form className="portal-preferences-form" onSubmit={(event) => void save(event)}>
          <label htmlFor="preferred-channel">Preferred contact method</label>
          <select id="preferred-channel" value={preferences.preferred_channel}
            disabled={saving}
            onChange={(event) => {
              setPreferences({ ...preferences, preferred_channel: event.target.value as Preferences['preferred_channel'] })
              setNotice(null)
            }}>
            <option value="portal">Patient portal</option>
            <option value="phone">Phone</option>
            <option value="email">Email</option>
          </select>
          <label className="portal-preferences-check">
            <input type="checkbox" checked={preferences.appointment_reminders}
              disabled={saving}
              onChange={(event) => {
                setPreferences({ ...preferences, appointment_reminders: event.target.checked })
                setNotice(null)
              }} />
            Appointment reminders
          </label>
          <label className="portal-preferences-check">
            <input type="checkbox" checked={preferences.care_updates}
              disabled={saving}
              onChange={(event) => {
                setPreferences({ ...preferences, care_updates: event.target.checked })
                setNotice(null)
              }} />
            General care updates
          </label>
          <button className="secondary-action-button" type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save preferences'}
          </button>
          {notice && <p role="status">{notice}</p>}
        </form>
      )}
    </section>
  )
}
