import { useEffect, useId, useState, type KeyboardEvent } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'

export type ReferenceKind = 'rxnorm' | 'cvx' | 'mvx'
export type ReferenceChoice = { code: string; name: string; kind: string; release: string; short_name?: string }
type Entry = Omit<ReferenceChoice, 'release'>
type Result = { query: string; status: 'ready'; release: string; results: Entry[] }
  | { query: string; status: 'error'; message: string }

const descriptions: Record<ReferenceKind, string> = {
  rxnorm: 'Search generic or brand names, formulations or RxCUI. Select a result to record its code.',
  cvx: 'Search vaccine names or CVX codes. Inactive and non-US formulations are for historical records.',
  mvx: 'Search manufacturer names or MVX codes. Leave blank if not documented.',
}

const termLabels: Record<string, string> = {
  IN: 'Ingredient', PIN: 'Precise ingredient', MIN: 'Multiple ingredients',
  BN: 'Brand', SCD: 'Generic product', SBD: 'Branded product', GPCK: 'Generic pack', BPCK: 'Brand pack',
}

type Props = {
  kind: ReferenceKind
  label: string
  value: string
  selected: ReferenceChoice | null
  onChange: (value: string) => void
  onSelect: (choice: ReferenceChoice) => void
  disabled?: boolean
  required?: boolean
  name?: string
}

export default function ReferencePicker({ kind, label, value, selected, onChange, onSelect, disabled, required, name }: Props) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [revision, setRevision] = useState(0)
  const [result, setResult] = useState<Result | null>(null)
  const query = value.trim().slice(0, 200)
  const current = result?.query === query ? result : null
  const options = current?.status === 'ready' ? current.results : []
  const expanded = open && !selected && options.length > 0

  useEffect(() => {
    if (!open || selected || query.length < 2 || disabled) return
    const controller = new AbortController()
    const timer = window.setTimeout(async () => {
      try {
        const response = await apiFetch(API_BASE_URL + '/clinical-reference/' + kind + '/search', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query }), signal: controller.signal,
        })
        if (!response.ok) throw new Error(await getApiErrorMessage(response))
        const data: { release: string; results: Entry[] } = await response.json()
        if (!controller.signal.aborted) {
          setResult({ query, status: 'ready', ...data })
          setActive(-1)
        }
      } catch (error) {
        if (!controller.signal.aborted) setResult({ query, status: 'error',
          message: error instanceof Error ? error.message : 'Reference unavailable.' })
      }
    }, 250)
    return () => { clearTimeout(timer); controller.abort() }
  }, [kind, open, query, selected, disabled, revision])

  useEffect(() => {
    if (expanded && active >= 0) document.getElementById(id + '-' + active)?.scrollIntoView({ block: 'nearest' })
  }, [expanded, active, id])

  function choose(item: Entry) {
    if (current?.status !== 'ready') return
    onSelect({ ...item, release: current.release })
    setOpen(false)
    setActive(-1)
  }

  function keyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape' && open) {
      event.preventDefault()
      setOpen(false)
      setActive(-1)
    } else if (!selected && (event.key === 'ArrowDown' || event.key === 'ArrowUp') && query.length >= 2) {
      event.preventDefault()
      setOpen(true)
      if (options.length) setActive(index => event.key === 'ArrowDown'
        ? Math.min(index + 1, options.length - 1)
        : index < 0 ? options.length - 1 : Math.max(0, index - 1))
    } else if (event.key === 'Enter' && expanded && active >= 0) {
      event.preventDefault()
      if (options[active]) choose(options[active])
    }
  }

  return <div className="diagnosis-picker reference-picker">
    <label className="form-field" htmlFor={id}>
      <span>{label}</span>
      <input id={id} name={name} value={value} required={required} disabled={disabled}
        maxLength={kind === 'cvx' ? 500 : 200} autoComplete="off" role="combobox" aria-autocomplete="list"
        aria-expanded={expanded} aria-controls={id + '-options'} aria-describedby={id + '-help'}
        aria-activedescendant={expanded && active >= 0 ? id + '-' + active : undefined}
        onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} onKeyDown={keyDown}
        onChange={event => { onChange(event.target.value); setOpen(true); setActive(-1) }} />
    </label>
    <p className="diagnosis-help" id={id + '-help'}>{descriptions[kind]}</p>
    {selected && <div className="diagnosis-selected"><strong className="diagnosis-code">{selected.code}</strong>
      <span>{selected.name}<small>{termLabels[selected.kind] || selected.kind} · {selected.release}</small></span></div>}
    <ul id={id + '-options'} className="diagnosis-options" role="listbox" aria-label={label.replace(' *', '') + ' matches'} hidden={!expanded}>
      {options.map((item, index) => <li key={item.code} id={id + '-' + index} role="option"
        aria-selected={index === active} className={index === active ? 'diagnosis-option-current' : undefined}
        onMouseDown={event => event.preventDefault()} onClick={() => choose(item)}>
        <strong className="diagnosis-code">{item.code}</strong>
        <span>{item.name}<small className="diagnosis-help">{termLabels[item.kind] || item.kind}</small></span>
      </li>)}
    </ul>
    {!selected && open && query.length >= 2 && <div className="diagnosis-search-status">
      {!current && <p role="status">Searching reference…</p>}
      {current?.status === 'ready' && <p role="status">{options.length ? options.length + ' matching concepts.' : 'No matching concepts. Try another name or code.'}</p>}
      {current?.status === 'error' && <p role="alert">{current.message}</p>}
    </div>}
    {!selected && current?.status === 'error' && <button type="button" className="secondary-action-button" disabled={disabled}
      onClick={() => { setOpen(true); setRevision(n => n + 1) }}>Retry reference search</button>}
  </div>
}
