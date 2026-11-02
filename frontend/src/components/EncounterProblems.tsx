import { useEffect, useState, type FormEvent } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Encounter, EncounterProblem, Problem } from '../types'

type EncounterProblemsProps = {
  encounter: Encounter
}

function EncounterProblems({ encounter }: EncounterProblemsProps) {
  const [links, setLinks] = useState<EncounterProblem[]>([])
  const [problems, setProblems] = useState<Problem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [pending, setPending] = useState<'add' | number | null>(null)
  const isFinalized = encounter.finalized_at !== null

  useEffect(() => {
    const controller = new AbortController()

    async function loadProblems() {
      setIsLoading(true)
      setLoadError(null)
      try {
        const response = await fetch(
          API_BASE_URL + '/encounters/' + encounter.id + '/problems',
          { signal: controller.signal }
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const linked: EncounterProblem[] = await response.json()

        if (isFinalized) {
          if (!controller.signal.aborted) setLinks(linked)
          return
        }

        const chartResponse = await fetch(
          API_BASE_URL + '/patients/' + encounter.patient_id + '/problems',
          { signal: controller.signal }
        )
        if (!chartResponse.ok) throw new Error(await getApiErrorMessage(chartResponse))
        const chartProblems: Problem[] = await chartResponse.json()

        if (!controller.signal.aborted) {
          setLinks(linked)
          setProblems(chartProblems)
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          console.error(requestError)
          setLoadError(
            requestError instanceof Error
              ? requestError.message
              : 'Linked problems could not be loaded.'
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadProblems()
    return () => controller.abort()
  }, [encounter.id, encounter.patient_id, isFinalized])

  const availableProblems = problems.filter(
    (problem) => !links.some((link) => link.problem_id === problem.id)
  )

  async function handleAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const problem = availableProblems.find((item) => String(item.id) === selectedId)
    if (!problem || pending !== null) return

    setActionError(null)
    setPending('add')
    try {
      const response = await fetch(
        API_BASE_URL + '/encounters/' + encounter.id + '/problems',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ problem_id: problem.id }),
        }
      )
      if (!response.ok) {
        setActionError(await getApiErrorMessage(response))
        return
      }
      const link: EncounterProblem = await response.json()
      setLinks((current) => [...current, link])
      setSelectedId('')
    } catch (requestError) {
      console.error(requestError)
      setActionError('The chart problem could not be linked.')
    } finally {
      setPending(null)
    }
  }

  async function handleRemove(problemId: number) {
    if (pending !== null) return
    setActionError(null)
    setPending(problemId)
    try {
      const response = await fetch(
        API_BASE_URL + '/encounters/' + encounter.id + '/problems/' + problemId,
        { method: 'DELETE' }
      )
      if (!response.ok) {
        setActionError(await getApiErrorMessage(response))
        return
      }
      setLinks((current) => current.filter((link) => link.problem_id !== problemId))
    } catch (requestError) {
      console.error(requestError)
      setActionError('The chart problem link could not be removed.')
    } finally {
      setPending(null)
    }
  }

  return (
    <section className="encounter-problems" aria-label="Linked chart problems">
      <h3>Linked Chart Problems</h3>
      {isLoading && <p role="status">Loading linked problems...</p>}
      {loadError && <p className="form-error" role="alert">{loadError}</p>}
      {!isLoading && !loadError && (
        <>
          {links.length === 0 && <p>No chart problems linked to this visit note.</p>}
          {links.length > 0 && (
            <ul className="encounter-problems-list">
              {links.map((link) => (
                <li className="encounter-problem-row" key={link.id}>
                  <div>
                    <strong>{link.problem_name_at_link}</strong>
                    <p className="encounter-meta">
                      {link.problem_status_at_link === 'active' ? 'Active' : 'Resolved'} when linked
                    </p>
                  </div>
                  {!isFinalized && (
                    <button
                      className="secondary-action-button"
                      type="button"
                      disabled={pending !== null}
                      aria-label={'Remove ' + link.problem_name_at_link + ' from this visit note'}
                      onClick={() => void handleRemove(link.problem_id)}
                    >
                      {pending === link.problem_id ? 'Removing...' : 'Remove'}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
          {isFinalized ? (
            <p className="encounter-help">These problem names and statuses are preserved as they were when linked.</p>
          ) : (
            <>
              {availableProblems.length > 0 ? (
                <form className="encounter-problem-form" onSubmit={(event) => void handleAdd(event)}>
                  <label className="form-field">
                    <span>Chart problem</span>
                    <select
                      value={selectedId}
                      onChange={(event) => setSelectedId(event.target.value)}
                      required
                      disabled={pending !== null}
                    >
                      <option value="">Choose a problem</option>
                      {availableProblems.map((problem) => (
                        <option key={problem.id} value={problem.id}>
                          {problem.name} ({problem.status === 'active' ? 'Active' : 'Resolved'})
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    className="secondary-action-button"
                    type="submit"
                    disabled={pending !== null || selectedId === ''}
                  >
                    {pending === 'add' ? 'Linking...' : 'Link problem'}
                  </button>
                </form>
              ) : (
                <p className="encounter-help">No additional chart problems are available to link.</p>
              )}
              <p className="encounter-help">Changes to problem links are allowed until this visit note is finalized.</p>
            </>
          )}
          {actionError && <p className="form-error" role="alert">{actionError}</p>}
        </>
      )}
    </section>
  )
}

export default EncounterProblems
