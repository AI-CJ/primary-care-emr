import { useEffect, useState } from 'react'

import { API_BASE_URL, apiFetch, getApiErrorMessage } from '../api'
import {
  canManagePatientLifecycle,
  nextPatientLifecycleAction,
  patientLifecycleStatus,
  type LifecycleAccount,
  type PatientLifecycleAction,
} from '../patientLifecycle'
import './PatientLifecycleControls.css'
import type { Patient } from '../types'

type PatientLifecycleControlsProps = {
  patientId: number
  onChanged?: (patient: Patient) => void
}

type LifecyclePatient = {
  id: number
  archived_at: string | null
}

export default function PatientLifecycleControls({ patientId, onChanged }: PatientLifecycleControlsProps) {
  const [account, setAccount] = useState<LifecycleAccount | null>(null)
  const [patient, setPatient] = useState<LifecyclePatient | null>(null)
  const [confirming, setConfirming] = useState<PatientLifecycleAction | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadLifecycleState() {
      setIsLoading(true)
      setError(null)
      try {
        const [accountResponse, patientResponse] = await Promise.all([
          apiFetch(`${API_BASE_URL}/auth/me`, { signal: controller.signal }),
          apiFetch(`${API_BASE_URL}/patients/${patientId}`, { signal: controller.signal }),
        ])
        if (!accountResponse.ok) throw new Error(await getApiErrorMessage(accountResponse))
        if (!patientResponse.ok) throw new Error(await getApiErrorMessage(patientResponse))
        const accountRecord = (await accountResponse.json()) as LifecycleAccount
        const patientRecord = (await patientResponse.json()) as LifecyclePatient
        if (!controller.signal.aborted) {
          setAccount(accountRecord)
          setPatient(patientRecord)
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof Error ? requestError.message : 'Chart status could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadLifecycleState()
    return () => controller.abort()
  }, [patientId])

  async function applyLifecycleAction(action: PatientLifecycleAction) {
    if (!patient || isSaving) return
    setIsSaving(true)
    setError(null)
    setMessage(null)
    try {
      const response = await apiFetch(
        `${API_BASE_URL}/patients/${patient.id}/${action}`,
        { method: 'POST' },
      )
      if (!response.ok) throw new Error(await getApiErrorMessage(response))
      const updated = (await response.json()) as Patient
      setPatient(updated)
      onChanged?.(updated)
      setConfirming(null)
      setMessage(
        action === 'archive'
          ? 'Chart archived. Historical records remain available and new writes are blocked.'
          : 'Chart reactivated. New clinical work can resume.',
      )
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Chart status could not be changed.')
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return <section className="overview-card lifecycle-card" aria-live="polite">Loading chart status...</section>
  }

  if (error && !patient) {
    return <section className="overview-card lifecycle-card"><p className="form-error" role="alert">{error}</p></section>
  }

  if (!patient) return null

  const status = patientLifecycleStatus(patient.archived_at)
  const nextAction = nextPatientLifecycleAction(patient.archived_at)
  const canManage = canManagePatientLifecycle(account)

  return (
    <section className={`overview-card lifecycle-card lifecycle-card-${status}`} aria-labelledby="patient-lifecycle-heading">
      <div className="overview-card-header lifecycle-card-header">
        <div>
          <p className="eyebrow">Patient lifecycle</p>
          <h2 id="patient-lifecycle-heading">
            {status === 'archived' ? 'Archived chart' : 'Active chart'}
          </h2>
        </div>
        <span className={`lifecycle-status lifecycle-status-${status}`}>
          {status === 'archived' ? 'Archived' : 'Active'}
        </span>
      </div>

      <p className="patient-timeline-help">
        {status === 'archived'
          ? 'Clinical history remains readable. New scheduling, documentation, orders, and patient portal sessions are blocked.'
          : 'The chart accepts normal clinical and administrative work.'}
      </p>

      {patient.archived_at && (
        <p className="lifecycle-date">Archived {new Date(patient.archived_at).toLocaleString()}</p>
      )}

      {canManage && confirming === null && (
        <button
          className={nextAction === 'archive' ? 'danger-button' : 'secondary-action-button'}
          type="button"
          onClick={() => setConfirming(nextAction)}
        >
          {nextAction === 'archive' ? 'Archive chart' : 'Reactivate chart'}
        </button>
      )}

      {canManage && confirming !== null && (
        <div className="lifecycle-confirmation" role="group" aria-label={`Confirm ${confirming}`}>
          <p>
            {confirming === 'archive'
              ? 'Archive this chart without deleting its clinical history? Scheduled or checked-in visits must be resolved first.'
              : 'Reactivate this chart and allow new clinical work? Existing portal sessions will not be restored.'}
          </p>
          <div className="lifecycle-actions">
            <button
              className={confirming === 'archive' ? 'danger-button' : 'secondary-action-button'}
              type="button"
              disabled={isSaving}
              onClick={() => void applyLifecycleAction(confirming)}
            >
              {isSaving ? 'Saving...' : `Confirm ${confirming}`}
            </button>
            <button
              className="secondary-action-button"
              type="button"
              disabled={isSaving}
              onClick={() => setConfirming(null)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {!canManage && (
        <p className="lifecycle-permission-note">Only administrators can change chart lifecycle status.</p>
      )}

      {error && <p className="form-error" role="alert">{error}</p>}
      {message && <p className="form-success" role="status">{message}</p>}
    </section>
  )
}
