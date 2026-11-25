/** A bounded worklist may contain more rows than the returned page. */
export function formatWorkQueueCount(count: number, limit?: number): string {
  return limit !== undefined && count >= limit ? String(limit) + '+' : String(count)
}
