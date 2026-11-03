import { useEffect, useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Encounter, EncounterMedication, Medication, MedicationStatus } from '../types'

const statusLabels: Record<MedicationStatus, string> = {
  active: 'Active',
  completed: 'Completed',
  discontinued: 'Discontinued',
}

type EncounterMedicationsProps = {
  encounter: Encounter
}

function EncounterMedications({ encounter }: EncounterMedicationsProps) {
  const [links, setLinks] = useState<EncounterMedication[]>([])
  const [medications, setMedications] = useState<Medication[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [pending, setPending] = useState<'add' | number | null>(null)
  const isFinalized = encounter.finalized_at !== null

  useEffect(() => {
    const controller = new AbortController()

    async function loadMedications() {
      setIsLoading(true)
      setLoadError(null)
      try {
        const response = await fetch(
          API_BASE_URL + '/encounters/' + encounter.id + '/medications',
          { signal: controller.signal }
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const linked: EncounterMedication[] = await response.json()

        if (isFinalized) {
          if (!controller.signal.aborted) setLinks(linked)
          return
        }

        const chartResponse = await fetch(
          API_BASE_URL + '/patients/' + encounter.patient_id + '/medications',
          { signal: controller.signal }
        )
        if (!chartResponse.ok) throw new Error(await getApiErrorMessage(chartResponse))
        const chartMedications: Medication[] = await chartResponse.json()

        if (!controller.signal.aborted) {
          setLinks(linked)
          setMedications(chartMedications)
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setLoadError(
            requestError instanceof Error
              ? requestError.message
              : 'Linked medications could not be loaded.'
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadMedications()
    return () => controller.abort()
  }, [encounter.id, encounter.patient_id, isFinalized])

  const availableMedications = medications.filter(
    (medication) => !links.some((link) => link.medication_id === medication.id)
  )

  async function handleAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const medication = availableMedications.find((item) => String(item.id) === selectedId)
    if (!medication || pending !== null) return

    setActionError(null)
    setPending('add')
    try {
      const response = await fetch(
        API_BASE_URL + '/encounters/' + encounter.id + '/medications',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ medication_id: medication.id }),
        }
      )
      if (!response.ok) {
        setActionError(await getApiErrorMessage(response))
        return
      }
      const link: EncounterMedication = await response.json()
      setLinks((current) => [...current, link])
      setSelectedId('')
    } catch (requestError) {
      console.error(requestError)
      setActionError('The chart medication could not be linked.')
    } finally {
      setPending(null)
    }
  }

  async function handleRemove(medicationId: number) {
    if (pending !== null) return
    setActionError(null)
    setPending(medicationId)
    try {
      const response = await fetch(
        API_BASE_URL + '/encounters/' + encounter.id + '/medications/' + medicationId,
        { method: 'DELETE' }
      )
      if (!response.ok) {
        setActionError(await getApiErrorMessage(response))
        return
      }
      setLinks((current) => current.filter((link) => link.medication_id !== medicationId))
    } catch (requestError) {
      console.error(requestError)
      setActionError('The chart medication link could not be removed.')
    } finally {
      setPending(null)
    }
  }

  return (
    <section className="encounter-medications" aria-label="Linked chart medications">
      <h3>Linked Chart Medications</h3>
      {isLoading && <p role="status">Loading linked medications...</p>}
      {loadError && <p className="form-error" role="alert">{loadError}</p>}
      {!isLoading && !loadError && (
        <>
          {links.length === 0 && <p>No chart medications linked to this visit note.</p>}
          {links.length > 0 && (
            <ul className="encounter-medications-list">
              {links.map((link) => (
                <li className="encounter-medication-row" key={link.id}>
                  <div>
                    <strong>
                      {link.name_at_link}{link.strength_at_link && ' ' + link.strength_at_link}
                    </strong>
                    <p className="encounter-meta">
                      {statusLabels[link.status_at_link]} when linked
                      {link.dose_at_link && ' · ' + link.dose_at_link}
                      {link.route_at_link && ' · ' + link.route_at_link}
                      {link.frequency_at_link && ' · ' + link.frequency_at_link}
                    </p>
                    {(link.start_date_at_link || link.end_date_at_link) && (
                      <p className="encounter-meta">
                        {link.start_date_at_link && 'Started ' + link.start_date_at_link}
                        {link.start_date_at_link && link.end_date_at_link && ' · '}
                        {link.end_date_at_link && 'Ended ' + link.end_date_at_link}
                      </p>
                    )}
                    {link.instructions_at_link && (
                      <p className="encounter-medication-instructions">
                        {link.instructions_at_link}
                      </p>
                    )}
                  </div>
                  {!isFinalized && (
                    <button
                      className="secondary-action-button"
                      type="button"
                      disabled={pending !== null}
                      aria-label={'Remove ' + link.name_at_link + ' from this visit note'}
                      onClick={() => void handleRemove(link.medication_id)}
                    >
                      {pending === link.medication_id ? 'Removing...' : 'Remove'}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
          {isFinalized ? (
            <p className="encounter-help">Medication details are preserved as they were when linked to this visit note.</p>
          ) : (
            <>
              {availableMedications.length > 0 ? (
                <form className="encounter-medication-form" onSubmit={(event) => void handleAdd(event)}>
                  <label className="form-field">
                    <span>Chart medication</span>
                    <select
                      value={selectedId}
                      onChange={(event) => setSelectedId(event.target.value)}
                      required
                      disabled={pending !== null}
                    >
                      <option value="">Choose a medication</option>
                      {availableMedications.map((medication) => (
                        <option key={medication.id} value={medication.id}>
                          {medication.name}{medication.strength && ' ' + medication.strength}
                          {' (' + statusLabels[medication.status] + ')'}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    className="secondary-action-button"
                    type="submit"
                    disabled={pending !== null || selectedId === ''}
                  >
                    {pending === 'add' ? 'Linking...' : 'Link medication'}
                  </button>
                </form>
              ) : (
                <p className="encounter-help">No additional chart medications are available to link.</p>
              )}
              <p className="encounter-help">Links can be changed until the note is finalized. Linking does not prescribe a medication or change the medication list.</p>
            </>
          )}
          {actionError && <p className="form-error" role="alert">{actionError}</p>}
        </>
      )}
    </section>
  )
}

export default EncounterMedications
