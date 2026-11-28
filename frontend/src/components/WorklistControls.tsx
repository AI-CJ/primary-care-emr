import { useId, type RefObject, type ReactNode } from 'react'
import './WorklistControls.css'

type Props = {
  label: string
  searchLabel: string
  placeholder: string
  summary: ReactNode
  query: string
  changeQuery: (query: string) => void
  clearSearch: () => void
  changePage: (page: number) => void
  summaryRef: RefObject<HTMLParagraphElement | null>
  searchRef: RefObject<HTMLInputElement | null>
  page: number
  pages: number
  start: number
  end: number
  matchingCount: number
}

export default function WorklistControls({
  label, searchLabel, placeholder, summary, query, changeQuery, clearSearch,
  changePage, summaryRef, searchRef, page, pages, start, end, matchingCount,
}: Props) {
  const searchId = useId()
  const summaryId = useId()

  return (
    <>
      <div className="worklist-search-toolbar" role="search" aria-label={label}>
        <div className="form-field">
          <label htmlFor={searchId}><span>{searchLabel}</span></label>
          <input id={searchId} ref={searchRef} type="search" value={query}
            placeholder={placeholder} aria-describedby={summaryId}
            onChange={event => changeQuery(event.target.value)} />
        </div>
        <button className="secondary-action-button" type="button"
          disabled={!query} onClick={clearSearch}>Clear search</button>
      </div>
      <div className="worklist-pagebar">
        <p id={summaryId} ref={summaryRef} tabIndex={-1} className="schedule-count" role="status" aria-atomic="true">
          {summary}
          {query.trim() && <> · {matchingCount} matching</>}
          {matchingCount > 0 && <> · Showing {start + 1}–{end} of {matchingCount}</>}
        </p>
        {pages > 1 && <nav aria-label={label + ' pages'}>
          <button type="button" className="secondary-action-button" disabled={page === 0}
            onClick={() => changePage(page - 1)}>Previous</button>
          <span>Page {page + 1} of {pages}</span>
          <button type="button" className="secondary-action-button" disabled={page + 1 >= pages}
            onClick={() => changePage(page + 1)}>Next</button>
        </nav>}
      </div>
    </>
  )
}
