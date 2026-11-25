/** Local worklist filtering preserves the API's priority and chronological order. */
export type LabQueueFilter = 'all' | 'urgent' | 'routine'
type QueueRow = { id: number; patient_name: string; test_name: string; priority: 'urgent' | 'routine' }
export const LAB_PAGE_SIZE = 6

export function filterLabQueue<T extends QueueRow>(orders: readonly T[], query: string, priority: LabQueueFilter): T[] {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean)
  return orders.filter(order => {
    if (priority !== 'all' && order.priority !== priority) return false
    const haystack = (order.patient_name + ' ' + order.test_name + ' ' + order.id).toLowerCase()
    return words.every(word => haystack.includes(word))
  })
}

export function labQueuePage<T>(rows: readonly T[], requestedPage: number) {
  const pages = Math.max(1, Math.ceil(rows.length / LAB_PAGE_SIZE))
  const page = Math.max(0, Math.min(requestedPage, pages - 1))
  const start = page * LAB_PAGE_SIZE
  return { page, pages, start, end: Math.min(start + LAB_PAGE_SIZE, rows.length), rows: rows.slice(start, start + LAB_PAGE_SIZE) }
}
