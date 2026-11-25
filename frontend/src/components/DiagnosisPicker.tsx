import { useEffect, useId, useState, type KeyboardEvent } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type { DiagnosisCode } from '../types'

export type SelectedDiagnosis = DiagnosisCode & { release: string }
type Result = { query: string; state: 'ready'; results: DiagnosisCode[]; release: string }
  | { query: string; state: 'error'; message: string }

type Props = {
  value: string
  selected: SelectedDiagnosis | null
  disabled: boolean
  onChange: (value: string) => void
  onSelect: (diagnosis: SelectedDiagnosis) => void
}

export default function DiagnosisPicker({ value, selected, disabled, onChange, onSelect }: Props) {
  const id = useId()
  const [result, setResult] = useState<Result | null>(null)
  const [active, setActive] = useState(-1)
  const [open, setOpen] = useState(false)
  const [revision, setRevision] = useState(0)
  const query = value.trim().slice(0, 200)
  const current = result?.query === query ? result : null
  const options = current?.state === 'ready' ? current.results : []
  const expanded = open && !selected && options.length > 0

  useEffect(() => {
    if (!open || selected || query.length < 2 || disabled) return
    const controller = new AbortController()
    const timer = window.setTimeout(async () => {
      try {
        const response = await apiFetch(API_BASE_URL + '/diagnosis-codes/search', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query }), signal: controller.signal,
        })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const data: { release: string; results: DiagnosisCode[] } = await response.json()
        if (!controller.signal.aborted) {
          setResult({ query, state: 'ready', ...data })
          setActive(-1)
        }
      } catch (error) {
        if (!controller.signal.aborted) setResult({ query, state: 'error',
          message: error instanceof Error ? error.message : 'Diagnosis lookup unavailable.' })
      }
    }, 250)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [query, open, selected, disabled, revision])

  function select(item: DiagnosisCode) {
    if (current?.state !== 'ready') return
    onSelect({ ...item, release: current.release })
    setOpen(false)
    setActive(-1)
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') {
      if (open) event.preventDefault()
      setOpen(false)
      setActive(-1)
    } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      if (!selected && query.length >= 2) {
        event.preventDefault()
        setOpen(true)
        if (options.length) setActive(index => event.key === 'ArrowDown'
          ? Math.min(index + 1, options.length - 1)
          : index < 0 ? options.length - 1 : Math.max(0, index - 1))
      }
    } else if (event.key === 'Enter' && expanded) {
      event.preventDefault()
      if (active >= 0 && options[active]) select(options[active])
    }
  }

  return <div className="diagnosis-picker">
    <label className="form-field" htmlFor={id}>
      <span>Problem *</span>
      <input id={id} name="name" type="text" required maxLength={512} autoComplete="off"
        placeholder="Search by diagnosis or ICD-10-CM code"
        role="combobox" aria-autocomplete="list" aria-expanded={expanded}
        aria-controls={id + '-options'} aria-describedby={id + '-help'}
        aria-activedescendant={expanded && active >= 0 ? id + '-option-' + active : undefined}
        value={value} disabled={disabled} onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)} onKeyDown={onKeyDown}
        onChange={event => { onChange(event.target.value); setOpen(true); setActive(-1) }} />
    </label>
    <p className="diagnosis-help" id={id + '-help'}>Search official ICD-10-CM descriptions by name or code. Use arrow keys and Enter, or choose a result.</p>
    {selected && <div className="diagnosis-selected">
      <strong className="diagnosis-code">{selected.code}</strong>
      <span>{selected.title}<small>ICD-10-CM {selected.release}</small></span>
    </div>}
    <ul role="listbox" id={id + '-options'} aria-label="Matching diagnoses" hidden={!expanded}
      className="diagnosis-options">
      {options.map((option, index) => <li key={option.code} id={id + '-option-' + index}
        role="option" aria-selected={index === active}
        onMouseDown={event => event.preventDefault()} onClick={() => select(option)}
        className={index === active ? 'diagnosis-option-current' : undefined}>
        <strong className="diagnosis-code">{option.code}</strong><span>{option.title}</span>
      </li>)}
    </ul>
    {open && !selected && query.length >= 2 && <div className="diagnosis-search-status">
      {!current && <p role="status">Searching diagnoses…</p>}
      {current?.state === 'ready' && <p role="status">{options.length ? options.length + (options.length === 20 ? ' shown; refine your search for more.' : ' matching diagnoses.') : 'No matching diagnoses. Try another term or code.'}</p>}
      {current?.state === 'error' && <p role="alert">{current.message}</p>}
    </div>}
    {current?.state === 'error' && !selected && <button type="button" className="secondary-action-button"
      onClick={() => { setOpen(true); setRevision(n => n + 1) }}>Retry diagnosis search</button>}
  </div>
}
