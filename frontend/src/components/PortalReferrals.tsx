import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { PortalReferralSummary } from '../types'

type PortalReferralsProps = {
  patientId: number
}

const statusLabels: Record<PortalReferralSummary['status'], string> = {
  requested: 'Recorded for follow-up',
  completed: 'Specialist visit documented',
  cancelled: 'Cancelled',
}

function PortalReferrals({ patientId }: PortalReferralsProps) {
  const [referrals, setReferrals] = useState<PortalReferralSummary[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadReferrals() {
      setIsLoading(true)
      setError(null)
      setReferrals(null)

      try {
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/portal-preview/referrals',
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: PortalReferralSummary[] = await response.json()
        if (!controller.signal.aborted) setReferrals(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof TypeError
            ? 'Referrals could not be loaded. Check your connection and try again.'
            : requestError instanceof Error
              ? requestError.message
              : 'Referrals could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadReferrals()
    return () => controller.abort()
  }, [patientId, refreshCount])

  const recentReferrals = referrals ?? []

  return (
    <section className="portal-card" aria-labelledby="portal-referrals">
      <h2 id="portal-referrals">My referrals</h2>
      <p className="portal-help">
        Recent specialist referrals from finalized visits in this fictional chart.
        Requests are not sent to outside clinics by this preview.
      </p>

      {isLoading && <p role="status">Loading referrals...</p>}
      {error && (
        <div>
          <p role="alert">{error}</p>
          <button
            type="button"
            className="secondary-action-button"
            onClick={() => setRefreshCount((count) => count + 1)}
          >
            Try Again
          </button>
        </div>
      )}
      {!isLoading && !error && recentReferrals.length === 0 && (
        <p>No specialist referrals are recorded in your chart.</p>
      )}
      {!isLoading && !error && recentReferrals.length > 0 && (
        <ul className="portal-records">
          {recentReferrals.map((referral) => (
            <li key={referral.id}>
              <strong>{referral.specialty}</strong>
              <span>Status: {statusLabels[referral.status]}</span>
              <span>
                Recorded at visit on <time dateTime={referral.visit_date}>
                  {referral.visit_date}
                </time>
              </span>
              {referral.priority === 'urgent' && <span>Marked urgent in this chart</span>}
              {referral.status === 'completed' && referral.seen_on && (
                <span>
                  Specialist visit recorded on <time dateTime={referral.seen_on}>
                    {referral.seen_on}
                  </time>
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default PortalReferrals
