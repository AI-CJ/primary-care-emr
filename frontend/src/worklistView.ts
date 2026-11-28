export const WORKLIST_PAGE_SIZE = 6

/** Keep the API's clinical ordering while searching the complete worklist. */
export function filterWorklist<T>(rows: readonly T[], query: string, searchText: (row: T) => string): T[] {
  const terms = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean)
  if (terms.length === 0) return [...rows]
  return rows.filter(row => {
    const text = searchText(row).toLocaleLowerCase()
    return terms.every(term => text.includes(term))
  })
}

export function worklistPage<T>(rows: readonly T[], requestedPage: number) {
  const pages = Math.max(1, Math.ceil(rows.length / WORKLIST_PAGE_SIZE))
  const page = Math.max(0, Math.min(requestedPage, pages - 1))
  const start = page * WORKLIST_PAGE_SIZE
  return {
    page, pages, start,
    end: Math.min(start + WORKLIST_PAGE_SIZE, rows.length),
    rows: rows.slice(start, start + WORKLIST_PAGE_SIZE),
  }
}
