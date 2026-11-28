import { DiagnosisLabel } from './DiagnosisIndications'
import { useCallback, useEffect, useId, useState } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type { Problem } from '../types'
import ProblemForm from './ProblemForm'
import { useInlineEditorFocus } from '../useInlineEditorFocus'

type ProblemListProps = {
  patientId: number
}

function ProblemList({ patientId }: ProblemListProps) {
  const [problems, setProblems] = useState<Problem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [editingProblem, setEditingProblem] = useState<Problem | null>(null)
  const [message, setMessage] = useState('')
  const headingId = useId()
  const { containerRef, rememberTrigger, returnToHeading } = useInlineEditorFocus(isAdding || editingProblem !== null)

  const loadProblems = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiFetch(
        API_BASE_URL + '/patients/' + patientId + '/problems'
      )

      if (!response.ok) {
        setError(await getApiErrorMessage(response))
        return
      }

      const data: Problem[] = await response.json()
      setProblems(data)
    } catch (requestError) {
      console.error(requestError)
      setError('Problems could not be loaded.')
    } finally {
      setIsLoading(false)
    }
  }, [patientId])

  useEffect(() => {
    let active = true
    queueMicrotask(() => {
      if (active) void loadProblems()
    })
    return () => { active = false }
  }, [loadProblems])

  function finishEditing() {
    returnToHeading()
    setIsAdding(false)
    setEditingProblem(null)
    setMessage('Problem saved.')
    void loadProblems()
  }

  return (
    <section className="overview-card problem-card" ref={containerRef} aria-labelledby={headingId}>
      <div className="overview-card-header">
        <h2 id={headingId}>Problems</h2>
        {!isAdding && !editingProblem && (
          <button
            className="secondary-action-button"
            type="button"
            data-editor-trigger="add"
            onClick={() => { rememberTrigger('add'); setMessage(''); setIsAdding(true) }}
          >
            + Add Problem
          </button>
        )}
      </div>

      <p role="status" aria-atomic="true" className="form-success editor-status">{message}</p>

      {isAdding && (
        <ProblemForm
          patientId={patientId}
          onSaved={finishEditing}
          onCancel={() => setIsAdding(false)}
        />
      )}

      {editingProblem && (
        <ProblemForm
          patientId={patientId}
          problem={editingProblem}
          onSaved={finishEditing}
          onCancel={() => setEditingProblem(null)}
        />
      )}

      {!isAdding && !editingProblem && isLoading && <p role="status">Loading problems...</p>}
      {!isAdding && !editingProblem && error && (
        <p className="form-error" role="alert">{error}</p>
      )}
      {!isAdding && !editingProblem && !isLoading && !error && problems.length === 0 && (
        <p>No problems recorded yet.</p>
      )}

      {!isAdding && !editingProblem && !isLoading && !error && problems.length > 0 && (
        <div className="problem-list">
          {problems.map((problem) => (
            <div className="problem-row" key={problem.id}>
              <div>
                <strong>{problem.name}</strong>
                <p className="problem-code-line"><DiagnosisLabel code={problem.icd10_code} /> {problem.icd10_release && <small>{problem.icd10_release}</small>}</p>
                {problem.icd10_title && problem.icd10_title !== problem.name && <p className="diagnosis-help">{problem.icd10_title}</p>}
                <p className="problem-meta">
                  {problem.status === 'active' ? 'Active' : 'Resolved'}
                  {problem.onset_date && ' · Onset ' + problem.onset_date}
                  {problem.resolved_date && ' · Resolved ' + problem.resolved_date}
                </p>
                {problem.notes && <p className="problem-notes">{problem.notes}</p>}
              </div>
              <button
                className="secondary-action-button"
                type="button"
                aria-label={'Edit problem: ' + problem.name}
                data-editor-trigger={'problem-' + problem.id}
                onClick={() => { rememberTrigger('problem-' + problem.id); setMessage(''); setEditingProblem(problem) }}
              >
                Edit
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default ProblemList
