import { useLayoutEffect, useRef, useState } from 'react'
import { filterWorklist, worklistPage } from './worklistView'

export function useWorklistView<T>(records: readonly T[] | null, searchText: (row: T) => string) {
  const [query, setQuery] = useState('')
  const [requestedPage, setRequestedPage] = useState(0)
  const [previousRecords, setPreviousRecords] = useState(records)
  const summaryRef = useRef<HTMLParagraphElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const focusPage = useRef(false)
  const matches = filterWorklist(records ?? [], query, searchText)
  const page = worklistPage(matches, requestedPage)

  // Keep the stored position at the displayed page after a shorter refresh.
  // Loading temporarily supplies null; it must not reset the user's position.
  if (records !== previousRecords) {
    setPreviousRecords(records)
    if (records !== null && requestedPage !== page.page) setRequestedPage(page.page)
  }

  useLayoutEffect(() => {
    if (!focusPage.current) return
    focusPage.current = false
    summaryRef.current?.focus()
  }, [requestedPage])

  function changeQuery(next: string) {
    focusPage.current = false
    setQuery(next)
    setRequestedPage(0)
  }

  function clearSearch() {
    changeQuery('')
    searchRef.current?.focus()
  }

  function changePage(next: number) {
    focusPage.current = true
    setRequestedPage(next)
  }

  return {
    rows: page.rows,
    controls: {
      query, changeQuery, clearSearch, changePage, summaryRef, searchRef,
      page: page.page, pages: page.pages, start: page.start, end: page.end,
      matchingCount: matches.length,
    },
  }
}
