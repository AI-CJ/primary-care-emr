import { useEffect, useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Allergy, AllergySeverity, AllergyStatus, Encounter, EncounterAllergy } from '../types'

const statusLabels: Record<AllergyStatus, string> = {
  active: 'Active',
  inactive: 'Inactive',
}

const severityLabels: Record<AllergySeverity, string> = {
  mild: 'Mild',
  moderate: 'Moderate',
  severe: 'Severe',
  unknown: 'Unknown severity',
}

type EncounterAllergiesProps = {
  encounter: Encounter
}

function EncounterAllergies({ encounter }: EncounterAllergiesProps) {
  const [links, setLinks] = useState<EncounterAllergy[]>([])
  const [allergies, setAllergies] = useState<Allergy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [pending, setPending] = useState<'add' | number | null>(null)
  const isFinalized = encounter.finalized_at !== null

  useEffect(() => {
    const controller = new AbortController()

    async function loadAllergies() {
      setIsLoading(true)
      setLoadError(null)
      setActionError(null)
      setSelectedId('')
      setLinks([])
      setAllergies([])
      try {
        const response = await fetch(
          API_BASE_URL + '/encounters/' + encounter.id + '/allergies',
          { signal: controller.signal }
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const linked: EncounterAllergy[] = await response.json()

        if (isFinalized) {
          if (!controller.signal.aborted) setLinks(linked)
          return
        }

        const chartResponse = await fetch(
          API_BASE_URL + '/patients/' + encounter.patient_id + '/allergies',
          { signal: controller.signal }
        )
        if (!chartResponse.ok) throw new Error(await getApiErrorMessage(chartResponse))
        const chartAllergies: Allergy[] = await chartResponse.json()

        if (!controller.signal.aborted) {
          setLinks(linked)
          setAllergies(chartAllergies)
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setLoadError(
            requestError instanceof Error
              ? requestError.message
              : 'Linked allergies could not be loaded.'
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadAllergies()
    return () => controller.abort()
  }, [encounter.id, encounter.patient_id, isFinalized])

  const availableAllergies = allergies.filter(
    (allergy) => !links.some((link) => link.allergy_id === allergy.id)
  )

  async function handleAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const allergy = availableAllergies.find((item) => String(item.id) === selectedId)
    if (!allergy || pending !== null || isFinalized) return

    setActionError(null)
    setPending('add')
    try {
      const response = await fetch(
        API_BASE_URL + '/encounters/' + encounter.id + '/allergies',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ allergy_id: allergy.id }),
        }
      )
      if (!response.ok) {
        setActionError(await getApiErrorMessage(response))
        return
      }
      const link: EncounterAllergy = await response.json()
      setLinks((current) => [...current, link])
      setSelectedId('')
    } catch (requestError) {
      console.error(requestError)
      setActionError('The chart allergy could not be linked.')
    } finally {
      setPending(null)
    }
  }

  async function handleRemove(allergyId: number) {
    if (pending !== null || isFinalized) return
    setActionError(null)
    setPending(allergyId)
    try {
      const response = await fetch(
        API_BASE_URL + '/encounters/' + encounter.id + '/allergies/' + allergyId,
        { method: 'DELETE' }
      )
      if (!response.ok) {
        setActionError(await getApiErrorMessage(response))
        return
      }
      setLinks((current) => current.filter((link) => link.allergy_id !== allergyId))
    } catch (requestError) {
      console.error(requestError)
      setActionError('The chart allergy link could not be removed.')
    } finally {
      setPending(null)
    }
  }

  return (
    <section className="encounter-allergies" aria-label="Linked chart allergies">
      <h3>Linked Chart Allergies</h3>
      {isLoading && <p role="status">Loading linked allergies...</p>}
      {loadError && <p className="form-error" role="alert">{loadError}</p>}
      {!isLoading && !loadError && (
        <>
          {links.length === 0 && <p>No chart allergies linked to this visit note.</p>}
          {links.length > 0 && (
            <ul className="encounter-allergies-list">
              {links.map((link) => (
                <li className="encounter-allergy-row" key={link.id}>
                  <div>
                    <strong>{link.allergen_at_link}</strong>
                    <p className="encounter-meta">
                      {statusLabels[link.status_at_link]} when linked
                      {' · ' + severityLabels[link.severity_at_link]}
                      {link.onset_date_at_link && ' · Onset ' + link.onset_date_at_link}
                    </p>
                    {link.reaction_at_link && (
                      <p className="encounter-meta">Reaction: {link.reaction_at_link}</p>
                    )}
                    {link.notes_at_link && (
                      <p className="encounter-allergy-notes">{link.notes_at_link}</p>
                    )}
                  </div>
                  {!isFinalized && (
                    <button
                      className="secondary-action-button"
                      type="button"
                      disabled={pending !== null}
                      aria-label={'Remove ' + link.allergen_at_link + ' from this visit note'}
                      onClick={() => void handleRemove(link.allergy_id)}
                    >
                      {pending === link.allergy_id ? 'Removing...' : 'Remove'}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
          {isFinalized ? (
            <p className="encounter-help">
              Allergy details are preserved as they were when linked to this visit note.
            </p>
          ) : (
            <>
              {availableAllergies.length > 0 ? (
                <form className="encounter-allergy-form" onSubmit={(event) => void handleAdd(event)}>
                  <label className="form-field">
                    <span>Chart allergy</span>
                    <select
                      value={selectedId}
                      onChange={(event) => setSelectedId(event.target.value)}
                      required
                      disabled={pending !== null}
                    >
                      <option value="">Choose an allergy</option>
                      {availableAllergies.map((allergy) => (
                        <option key={allergy.id} value={allergy.id}>
                          {allergy.allergen}
                          {' (' + statusLabels[allergy.status] + ', ' + severityLabels[allergy.severity] + ')'}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    className="secondary-action-button"
                    type="submit"
                    disabled={pending !== null || selectedId === ''}
                  >
                    {pending === 'add' ? 'Linking...' : 'Link allergy'}
                  </button>
                </form>
              ) : (
                <p className="encounter-help">No additional chart allergies are available to link.</p>
              )}
              <p className="encounter-help">
                Links can be changed until the note is finalized. Linking does not change the patient's allergy list.
              </p>
            </>
          )}
          {actionError && <p className="form-error" role="alert">{actionError}</p>}
        </>
      )}
    </section>
  )
}

export default EncounterAllergies
