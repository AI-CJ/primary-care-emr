import { useCallback, useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { Problem } from '../types'
import ProblemForm from './ProblemForm'

type ProblemListProps = {
  patientId: number
}

function ProblemList({ patientId }: ProblemListProps) {
  const [problems, setProblems] = useState<Problem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [editingProblem, setEditingProblem] = useState<Problem | null>(null)

  const loadProblems = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(
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
    void loadProblems()
  }, [loadProblems])

  function finishEditing() {
    setIsAdding(false)
    setEditingProblem(null)
    void loadProblems()
  }

  return (
    <section className="overview-card problem-card">
      <div className="overview-card-header">
        <h2>Problems</h2>
        {!isAdding && !editingProblem && (
          <button
            className="secondary-action-button"
            type="button"
            onClick={() => setIsAdding(true)}
          >
            + Add Problem
          </button>
        )}
      </div>

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

      {!isAdding && !editingProblem && isLoading && <p>Loading problems...</p>}
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
                onClick={() => setEditingProblem(problem)}
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
