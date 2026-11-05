import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { PatientReferral } from '../types'

type PatientReferralHistoryProps = {
  patientId: number
}

const statusLabels: Record<PatientReferral['status'], string> = {
  requested: 'Pending',
  completed: 'Completed',
  cancelled: 'Cancelled',
}

function PatientReferralHistory({ patientId }: PatientReferralHistoryProps) {
  const [referrals, setReferrals] = useState<PatientReferral[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadReferrals() {
      setIsLoading(true)
      setError(null)
      setReferrals([])

      try {
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/referrals',
          { signal: controller.signal }
        )
        if (!response.ok) {
          throw new Error(await getApiErrorMessage(response))
        }
        const records: PatientReferral[] = await response.json()
        if (!controller.signal.aborted) setReferrals(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Referral history could not be loaded.'
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadReferrals()
    return () => controller.abort()
  }, [patientId, reloadCount])

  return (
    <section className="overview-card patient-referral-card" aria-labelledby="patient-referral-heading">
      <div className="overview-card-header">
        <h2 id="patient-referral-heading">Referral History</h2>
        <button
          className="secondary-action-button"
          type="button"
          disabled={isLoading}
          onClick={() => setReloadCount((count) => count + 1)}
        >
          Refresh
        </button>
      </div>

      {isLoading && <p role="status">Loading referral history...</p>}
      {error && (
        <div>
          <p className="form-error" role="alert">{error}</p>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setReloadCount((count) => count + 1)}
          >
            Try Again
          </button>
        </div>
      )}
      {!isLoading && !error && referrals.length === 0 && (
        <p>No referrals recorded for this patient.</p>
      )}
      {!isLoading && !error && referrals.length > 0 && (
        <ul className="patient-referral-list">
          {referrals.map((referral) => (
            <li className="patient-referral-row" key={referral.id}>
              <div className="patient-referral-row-header">
                <strong>{referral.specialty}</strong>
                <span className="patient-referral-status">{statusLabels[referral.status]}</span>
              </div>
              <p className="encounter-meta">
                Visit <time dateTime={referral.visit_date}>{referral.visit_date}</time>
                {' · '}
                {referral.priority === 'urgent' ? 'Urgent' : 'Routine'}
                {' · '}
                Referral #{referral.id}
              </p>
              <p className="patient-referral-details">Reason: {referral.reason}</p>
              {referral.status === 'cancelled' && (
                <p className="patient-referral-details">
                  Cancellation reason: {referral.cancellation_reason ?? 'Not recorded'}
                </p>
              )}
              {referral.status === 'completed' && (
                <div className="patient-referral-follow-up">
                  <strong>Specialist follow-up</strong>
                  {referral.seen_on && (
                    <p className="encounter-meta">
                      Seen <time dateTime={referral.seen_on}>{referral.seen_on}</time>
                    </p>
                  )}
                  <p className="patient-referral-details">
                    {referral.follow_up_summary ?? 'No follow-up summary recorded.'}
                  </p>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      <p className="encounter-help">
        Demo only: referral requests are stored in the chart, not sent to specialists.
      </p>
    </section>
  )
}

export default PatientReferralHistory
