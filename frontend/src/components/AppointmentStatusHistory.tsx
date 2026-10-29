import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { AppointmentStatus, AppointmentStatusChange } from '../types'

type AppointmentStatusHistoryProps = {
  appointmentId: number
}

const statusLabels: Record<AppointmentStatus, string> = {
  scheduled: 'Scheduled',
  checked_in: 'Checked in',
  completed: 'Completed',
  cancelled: 'Cancelled',
}

function AppointmentStatusHistory({
  appointmentId,
}: AppointmentStatusHistoryProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [changes, setChanges] = useState<AppointmentStatusChange[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen) return

    const controller = new AbortController()

    async function loadHistory() {
      setIsLoading(true)
      setError(null)

      try {
        const response = await fetch(
          API_BASE_URL + '/appointments/' + appointmentId + '/status-history',
          { signal: controller.signal }
        )

        if (!response.ok) {
          const message = await getApiErrorMessage(response)
          if (!controller.signal.aborted) setError(message)
          return
        }

        const records: AppointmentStatusChange[] = await response.json()
        if (!controller.signal.aborted) setChanges(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setError('Status history could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadHistory()
    return () => controller.abort()
  }, [appointmentId, isOpen])

  const detailsId = 'appointment-status-history-' + appointmentId

  return (
    <div className="appointment-history">
      <button
        className="appointment-history-toggle"
        type="button"
        aria-expanded={isOpen}
        aria-controls={detailsId}
        onClick={() => setIsOpen((open) => !open)}
      >
        {isOpen ? 'Hide status history' : 'View status history'}
      </button>

      <div id={detailsId} hidden={!isOpen}>
        {isLoading && <p role="status">Loading status history...</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
        {!isLoading && !error && changes.length === 0 && (
          <p className="appointment-history-empty">
            No status history recorded since tracking began.
          </p>
        )}
        {!isLoading && !error && changes.length > 0 && (
          <ol className="appointment-history-list">
            {changes.map((change) => (
              <li key={change.id}>
                <time dateTime={change.changed_at}>
                  {new Date(change.changed_at).toLocaleString()}
                </time>
                {' · '}
                {change.previous_status === null
                  ? 'Created as ' + statusLabels[change.new_status]
                  : statusLabels[change.previous_status] +
                    ' → ' + statusLabels[change.new_status]}
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  )
}

export default AppointmentStatusHistory
