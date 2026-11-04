import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Encounter, Referral, ReferralInput, ReferralPriority } from '../types'

type EncounterReferralsProps = {
  encounter: Encounter
}

function EncounterReferrals({ encounter }: EncounterReferralsProps) {
  const [referrals, setReferrals] = useState<Referral[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [cancelReferralId, setCancelReferralId] = useState<number | null>(null)
  const [cancellationReason, setCancellationReason] = useState('')
  const [isCancelling, setIsCancelling] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [specialty, setSpecialty] = useState('')
  const [reason, setReason] = useState('')
  const [priority, setPriority] = useState<ReferralPriority>('routine')
  const isFinalized = encounter.finalized_at !== null

  useEffect(() => {
    const controller = new AbortController()

    async function loadReferrals() {
      setIsLoading(true)
      setLoadError(null)
      setReferrals([])
      try {
        const response = await fetch(
          `${API_BASE_URL}/encounters/${encounter.id}/referrals`,
          { signal: controller.signal }
        )
        if (!response.ok) {
          throw new Error(await getApiErrorMessage(response))
        }
        const records: Referral[] = await response.json()
        if (!controller.signal.aborted) setReferrals(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setLoadError(
            requestError instanceof Error
              ? requestError.message
              : 'Referrals could not be loaded.'
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadReferrals()
    return () => controller.abort()
  }, [encounter.id, retryCount])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const cleanedSpecialty = specialty.trim()
    const cleanedReason = reason.trim()
    if (isSaving || isFinalized || !cleanedSpecialty || !cleanedReason) return

    const referralData: ReferralInput = {
      specialty: cleanedSpecialty,
      reason: cleanedReason,
      priority,
    }

    setIsSaving(true)
    setSaveError(null)
    setSuccessMessage(null)
    try {
      const response = await fetch(
        `${API_BASE_URL}/encounters/${encounter.id}/referrals`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(referralData),
        }
      )
      if (!response.ok) {
        setSaveError(await getApiErrorMessage(response))
        return
      }
      const saved: Referral = await response.json()
      setReferrals((current) => [...current, saved])
      setSpecialty('')
      setReason('')
      setPriority('routine')
      setSuccessMessage('Referral request recorded for this visit.')
    } catch (requestError) {
      console.error(requestError)
      setSaveError('The referral request could not be saved.')
    } finally {
      setIsSaving(false)
    }
  }

  async function handleCancel(event: FormEvent<HTMLFormElement>, referral: Referral) {
    event.preventDefault()
    const reason = cancellationReason.trim()
    if (isCancelling || !reason || referral.status !== 'requested') return
    if (!window.confirm('Cancel this referral request? This cannot be undone.')) return

    setIsCancelling(true)
    setSaveError(null)
    setSuccessMessage(null)
    try {
      const response = await fetch(
        `${API_BASE_URL}/referrals/${referral.id}/cancel`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason }),
        }
      )
      if (!response.ok) {
        setSaveError(await getApiErrorMessage(response))
        return
      }
      const saved: Referral = await response.json()
      setReferrals((current) => current.map((entry) =>
        entry.id === saved.id ? saved : entry
      ))
      setCancelReferralId(null)
      setCancellationReason('')
      setSuccessMessage('Referral cancelled. The original request remains in the chart.')
    } catch (requestError) {
      console.error(requestError)
      setSaveError('The referral request could not be cancelled.')
    } finally {
      setIsCancelling(false)
    }
  }

  return (
    <section className="encounter-referrals" aria-label="Visit referrals">
      <h3>Specialist Referrals</h3>
      {isLoading && <p role="status">Loading referrals...</p>}
      {loadError && (
        <div>
          <p className="form-error" role="alert">{loadError}</p>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setRetryCount((count) => count + 1)}
          >
            Retry Loading
          </button>
        </div>
      )}
      {!isLoading && !loadError && (
        <>
          {referrals.length === 0 && <p>No referrals recorded for this visit.</p>}
          {referrals.length > 0 && (
            <ul className="encounter-referral-list">
              {referrals.map((referral) => (
                <li className="encounter-referral-row" key={referral.id}>
                  <strong>{referral.specialty}</strong>
                  <p className="encounter-meta">
                    {referral.priority === 'urgent' ? 'Urgent' : 'Routine'}
                    {referral.status === 'cancelled' ? ' · Cancelled · ' : referral.status === 'completed' ? ' · Completed · ' : ' · Request recorded · '}
                    <time dateTime={referral.requested_at}>
                      {new Date(referral.requested_at).toLocaleString()}
                    </time>
                  </p>
                  <p className="encounter-referral-reason">Reason: {referral.reason}</p>
                  {referral.status === 'cancelled' && (
                    <p className="encounter-referral-reason">
                      Cancellation reason: {referral.cancellation_reason}
                      {referral.cancelled_at && (
                        <> · <time dateTime={referral.cancelled_at}>
                          {new Date(referral.cancelled_at).toLocaleString()}
                        </time></>
                      )}
                    </p>
                  )}
                  {referral.status === 'completed' && (
                    <p className="encounter-referral-reason">
                      Specialist seen: {referral.seen_on ?? 'Date not recorded'}
                      {' · '}Follow-up: {referral.follow_up_summary}
                      {referral.completed_at && (
                        <> · Recorded <time dateTime={referral.completed_at}>
                          {new Date(referral.completed_at).toLocaleString()}
                        </time></>
                      )}
                    </p>
                  )}
                  {referral.status === 'requested' && (
                    cancelReferralId === referral.id ? (
                      <form className="encounter-referral-form" onSubmit={(event) => void handleCancel(event, referral)}>
                        <label className="form-field">
                          <span>Reason for cancelling {referral.specialty} *</span>
                          <textarea
                            value={cancellationReason}
                            onChange={(event) => setCancellationReason(event.target.value)}
                            maxLength={1000}
                            rows={2}
                            required
                            disabled={isCancelling}
                          />
                        </label>
                        <div className="encounter-form-actions">
                          <button className="secondary-action-button" type="submit" disabled={isCancelling || !cancellationReason.trim()}>
                            {isCancelling ? 'Cancelling...' : 'Confirm Cancellation'}
                          </button>
                          <button className="secondary-action-button" type="button" disabled={isCancelling} onClick={() => {
                            setCancelReferralId(null)
                            setCancellationReason('')
                            setSaveError(null)
                          }}>
                            Keep Referral
                          </button>
                        </div>
                      </form>
                    ) : (
                      <button className="secondary-action-button" type="button" disabled={isCancelling} onClick={() => {
                        setCancelReferralId(referral.id)
                        setCancellationReason('')
                        setSaveError(null)
                        setSuccessMessage(null)
                      }}>
                        Cancel Referral
                      </button>
                    )
                  )}
                </li>
              ))}
            </ul>
          )}
          {isFinalized ? (
            <p className="encounter-help">
              New referrals cannot be added after the visit note is finalized. Pending referrals may still be cancelled.
            </p>
          ) : (
            <form className="encounter-referral-form" onSubmit={(event: FormEvent<HTMLFormElement>) => void handleSubmit(event)}>
              <label className="form-field">
                <span>Specialty *</span>
                <input
                  type="text"
                  value={specialty}
                  onChange={(event: ChangeEvent<HTMLInputElement>) => setSpecialty(event.target.value)}
                  maxLength={200}
                  required
                  disabled={isSaving}
                />
              </label>
              <label className="form-field">
                <span>Reason for referral *</span>
                <textarea
                  value={reason}
                  onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setReason(event.target.value)}
                  maxLength={1000}
                  rows={3}
                  required
                  disabled={isSaving}
                />
              </label>
              <label className="form-field">
                <span>Priority</span>
                <select
                  value={priority}
                  onChange={(event: ChangeEvent<HTMLSelectElement>) => setPriority(event.target.value as ReferralPriority)}
                  disabled={isSaving}
                >
                  <option value="routine">Routine</option>
                  <option value="urgent">Urgent</option>
                </select>
              </label>
              <button
                className="secondary-action-button"
                type="submit"
                disabled={isSaving || !specialty.trim() || !reason.trim()}
              >
                {isSaving ? 'Recording...' : 'Add Referral'}
              </button>
            </form>
          )}
          <p className="encounter-help">
            Demo only: referral requests are stored in the chart, not sent to specialists.
          </p>
          {saveError && <p className="form-error" role="alert">{saveError}</p>}
          {successMessage && <p role="status">{successMessage}</p>}
        </>
      )}
    </section>
  )
}

export default EncounterReferrals
