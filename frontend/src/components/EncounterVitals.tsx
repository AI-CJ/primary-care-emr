import { useEffect, useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Encounter, EncounterVital, Vital } from '../types'

type EncounterVitalsProps = {
  encounter: Encounter
}

type Measurements = Pick<
  Vital,
  | 'systolic_bp'
  | 'diastolic_bp'
  | 'heart_rate'
  | 'respiratory_rate'
  | 'temperature_c'
  | 'oxygen_saturation'
  | 'height_cm'
  | 'weight_kg'
>

function formatMeasurements(vital: Measurements): string {
  const details: string[] = []
  if (vital.systolic_bp !== null && vital.diastolic_bp !== null) {
    details.push('BP ' + vital.systolic_bp + '/' + vital.diastolic_bp + ' mmHg')
  }
  if (vital.heart_rate !== null) details.push('Pulse ' + vital.heart_rate + ' bpm')
  if (vital.respiratory_rate !== null) details.push('Respirations ' + vital.respiratory_rate + '/min')
  if (vital.temperature_c !== null) details.push('Temperature ' + vital.temperature_c + ' °C')
  if (vital.oxygen_saturation !== null) details.push('SpO₂ ' + vital.oxygen_saturation + '%')
  if (vital.height_cm !== null) details.push('Height ' + vital.height_cm + ' cm')
  if (vital.weight_kg !== null) details.push('Weight ' + vital.weight_kg + ' kg')
  return details.join(' · ')
}

function snapshotMeasurements(link: EncounterVital): Measurements {
  return {
    systolic_bp: link.systolic_bp_at_link,
    diastolic_bp: link.diastolic_bp_at_link,
    heart_rate: link.heart_rate_at_link,
    respiratory_rate: link.respiratory_rate_at_link,
    temperature_c: link.temperature_c_at_link,
    oxygen_saturation: link.oxygen_saturation_at_link,
    height_cm: link.height_cm_at_link,
    weight_kg: link.weight_kg_at_link,
  }
}

function EncounterVitals({ encounter }: EncounterVitalsProps) {
  const [links, setLinks] = useState<EncounterVital[]>([])
  const [chartVitals, setChartVitals] = useState<Vital[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [pending, setPending] = useState<'add' | number | null>(null)
  const isFinalized = encounter.finalized_at !== null

  useEffect(() => {
    const controller = new AbortController()

    async function loadVitals() {
      setIsLoading(true)
      setLoadError(null)
      setLinks([])
      setChartVitals([])
      try {
        const response = await fetch(
          API_BASE_URL + '/encounters/' + encounter.id + '/vitals',
          { signal: controller.signal }
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const linked: EncounterVital[] = await response.json()

        if (isFinalized) {
          if (!controller.signal.aborted) setLinks(linked)
          return
        }

        const chartResponse = await fetch(
          API_BASE_URL + '/patients/' + encounter.patient_id + '/vitals',
          { signal: controller.signal }
        )
        if (!chartResponse.ok) throw new Error(await getApiErrorMessage(chartResponse))
        const chart: Vital[] = await chartResponse.json()

        if (!controller.signal.aborted) {
          setLinks(linked)
          setChartVitals(chart)
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setLoadError(
            requestError instanceof Error
              ? requestError.message
              : 'Visit vitals could not be loaded.'
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadVitals()
    return () => controller.abort()
  }, [encounter.id, encounter.patient_id, encounter.visit_date, isFinalized])

  const availableVitals = chartVitals.filter(
    (vital) =>
      vital.recorded_on === encounter.visit_date &&
      !links.some((link) => link.vital_id === vital.id)
  )

  async function handleAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const vital = availableVitals.find((item) => String(item.id) === selectedId)
    if (!vital || pending !== null) return

    setActionError(null)
    setPending('add')
    try {
      const response = await fetch(
        API_BASE_URL + '/encounters/' + encounter.id + '/vitals',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ vital_id: vital.id }),
        }
      )
      if (!response.ok) {
        setActionError(await getApiErrorMessage(response))
        return
      }
      const link: EncounterVital = await response.json()
      setLinks((current) => [...current, link])
      setSelectedId('')
    } catch (requestError) {
      console.error(requestError)
      setActionError('The vitals record could not be linked.')
    } finally {
      setPending(null)
    }
  }

  async function handleRemove(vitalId: number) {
    if (pending !== null) return
    setActionError(null)
    setPending(vitalId)
    try {
      const response = await fetch(
        API_BASE_URL + '/encounters/' + encounter.id + '/vitals/' + vitalId,
        { method: 'DELETE' }
      )
      if (!response.ok) {
        setActionError(await getApiErrorMessage(response))
        return
      }
      setLinks((current) => current.filter((link) => link.vital_id !== vitalId))
    } catch (requestError) {
      console.error(requestError)
      setActionError('The vitals link could not be removed.')
    } finally {
      setPending(null)
    }
  }

  return (
    <section className="encounter-vitals" aria-label="Visit vitals">
      <h3>Visit Vitals</h3>
      {isLoading && <p role="status">Loading visit vitals...</p>}
      {loadError && <p className="form-error" role="alert">{loadError}</p>}
      {!isLoading && !loadError && (
        <>
          {links.length === 0 && <p>No vitals linked to this visit note.</p>}
          {links.length > 0 && (
            <ul className="encounter-vitals-list">
              {links.map((link) => (
                <li className="encounter-vital-row" key={link.id}>
                  <div>
                    <strong>Recorded {link.recorded_on_at_link}</strong>
                    <p className="encounter-meta">{formatMeasurements(snapshotMeasurements(link))}</p>
                    {link.notes_at_link && <p className="encounter-meta">{link.notes_at_link}</p>}
                  </div>
                  {!isFinalized && (
                    <button
                      className="secondary-action-button"
                      type="button"
                      disabled={pending !== null}
                      aria-label={'Remove vitals record #' + link.vital_id + ' from this visit note'}
                      onClick={() => void handleRemove(link.vital_id)}
                    >
                      {pending === link.vital_id ? 'Removing...' : 'Remove'}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
          {isFinalized ? (
            <p className="encounter-help">
              These measurements were saved when linked and are read-only after finalization.
            </p>
          ) : (
            <>
              {availableVitals.length > 0 ? (
                <form className="encounter-vital-form" onSubmit={(event) => void handleAdd(event)}>
                  <label className="form-field">
                    <span>Recorded vitals from {encounter.visit_date}</span>
                    <select
                      value={selectedId}
                      onChange={(event) => setSelectedId(event.target.value)}
                      required
                      disabled={pending !== null}
                    >
                      <option value="">Choose a vitals record</option>
                      {availableVitals.map((vital) => (
                        <option key={vital.id} value={vital.id}>
                          {'#' + vital.id + ' · ' + formatMeasurements(vital)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    className="secondary-action-button"
                    type="submit"
                    disabled={pending !== null || selectedId === ''}
                  >
                    {pending === 'add' ? 'Linking...' : 'Link vitals'}
                  </button>
                </form>
              ) : (
                <p className="encounter-help">No additional vitals recorded on this visit date are available.</p>
              )}
              <p className="encounter-help">Vitals links can be changed until the visit note is finalized.</p>
            </>
          )}
          {actionError && <p className="form-error" role="alert">{actionError}</p>}
        </>
      )}
    </section>
  )
}

export default EncounterVitals
