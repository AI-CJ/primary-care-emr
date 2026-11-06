import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Referral } from '../types'

type PendingReferral = Referral & {
  patient_id: number
  patient_name: string
  visit_date: string
}

type PendingReferralWorklistProps = {
  onBack: () => void
  onOpenPatient: (patientId: number) => void
  patientError: string | null
}

function PendingReferralWorklist({
  onBack,
  onOpenPatient,
  patientError,
}: PendingReferralWorklistProps) {
  const [referrals, setReferrals] = useState<PendingReferral[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setReferrals(null)
    setError(null)

    async function loadReferrals() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/worklists/pending-referrals`,
          { signal: controller.signal },
        )
        if (!response.ok) {
          throw new Error(await getApiErrorMessage(response))
        }

        const records: PendingReferral[] = await response.json()
        if (!controller.signal.aborted) setReferrals(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(
            requestError instanceof TypeError
              ? 'The server could not be reached. Try again.'
              : requestError instanceof Error
                ? requestError.message
                : 'Pending referrals could not be loaded.',
          )
        }
      }
    }

    void loadReferrals()
    return () => controller.abort()
  }, [refreshCount])

  return (
    <main className="search-page">
      <section
        className="search-panel schedule-panel"
        aria-labelledby="pending-referrals-heading"
      >
        <button className="back-button" type="button" onClick={onBack}>
          ← Back to patient search
        </button>
        <div className="search-panel-header">
          <div>
            <h1 id="pending-referrals-heading">Pending Referrals</h1>
            <p className="pending-lab-intro">
              Outstanding specialist referrals, urgent first and oldest within
              each priority. Open a chart to record follow-up or cancel a request.
            </p>
          </div>
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setRefreshCount((count) => count + 1)}
            disabled={referrals === null && error === null}
          >
            Refresh
          </button>
        </div>

        {patientError && (
          <p className="form-error" role="alert">{patientError}</p>
        )}
        {!referrals && !error && (
          <p className="empty-message" role="status">
            Loading pending referrals...
          </p>
        )}
        {error && (
          <div>
            <p className="form-error" role="alert">{error}</p>
            <button
              className="secondary-action-button"
              type="button"
              onClick={() => setRefreshCount((count) => count + 1)}
            >
              Try Again
            </button>
          </div>
        )}
        {referrals && (
          <>
            <p className="schedule-count" role="status">
              {referrals.length} pending referral{referrals.length === 1 ? '' : 's'}
            </p>
            {referrals.length === 0 ? (
              <p className="empty-message">No pending referrals.</p>
            ) : (
              <ol className="pending-lab-list">
                {referrals.map((referral) => (
                  <li className="pending-lab-row" key={referral.id}>
                    <div>
                      <div className="pending-lab-title">
                        <strong>{referral.specialty}</strong>
                        <span
                          className={referral.priority === 'urgent'
                            ? 'pending-lab-priority pending-lab-priority-urgent'
                            : 'pending-lab-priority'}
                        >
                          {referral.priority === 'urgent' ? 'Urgent' : 'Routine'}
                        </span>
                      </div>
                      <p className="pending-lab-meta">
                        Visit <time dateTime={referral.visit_date}>
                          {referral.visit_date}
                        </time>
                        {' · '}
                        Requested <time dateTime={referral.requested_at}>
                          {new Date(referral.requested_at).toLocaleString()}
                        </time>
                        {' · '}
                        Referral #{referral.id}
                      </p>
                      <p className="pending-lab-reason">
                        Reason: {referral.reason}
                      </p>
                    </div>
                    <div className="pending-lab-patient">
                      <button
                        className="schedule-patient-link"
                        type="button"
                        onClick={() => onOpenPatient(referral.patient_id)}
                      >
                        {referral.patient_name}
                      </button>
                      <span>Open patient chart</span>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
        <p className="pending-lab-disclaimer">
          Synthetic-data demonstration. No referrals are sent to specialists.
        </p>
      </section>
    </main>
  )
}

export default PendingReferralWorklist
