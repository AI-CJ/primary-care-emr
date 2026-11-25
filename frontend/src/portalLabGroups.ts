import type { PortalLabOrder, PortalLabResult } from './types'

export type ReleasedOrder = PortalLabOrder & { result: PortalLabResult }

/** The server is responsible for releasing and scoping results. Null is never a result. */
export function groupPortalLabOrders(records: readonly PortalLabOrder[]) {
  const newestRequest = (a: PortalLabOrder, b: PortalLabOrder) =>
    b.ordered_at.localeCompare(a.ordered_at) || b.id - a.id
  const released = records.filter((item): item is ReleasedOrder => item.status === 'resulted' && item.result !== null)
    .sort((a,b) => b.result.reported_at.localeCompare(a.result.reported_at) || b.id - a.id)
  return {
    recent: released.slice(0,3),
    older: released.slice(3),
    pending: records.filter(item => item.status === 'ordered').sort(newestRequest),
    awaitingRelease: records.filter(item => item.status === 'resulted' && item.result === null).sort(newestRequest),
    cancelled: records.filter(item => item.status === 'cancelled').sort((a,b) =>
      (b.cancelled_at ?? b.ordered_at).localeCompare(a.cancelled_at ?? a.ordered_at) || b.id - a.id),
  }
}
