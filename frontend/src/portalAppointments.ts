import type { PortalAppointmentSummary } from './types'

const isOpen = (item: PortalAppointmentSummary) => item.status === 'scheduled' || item.status === 'checked_in'

/** Preserve the clinic's recorded local calendar date; do not convert it to UTC. */
export function groupPortalAppointments(records: readonly PortalAppointmentSummary[], today: string) {
  const chronological = (a: PortalAppointmentSummary, b: PortalAppointmentSummary) =>
    a.scheduled_date.localeCompare(b.scheduled_date) || a.start_time.localeCompare(b.start_time) || a.id - b.id
  return {
    upcoming: records.filter(item => isOpen(item) && item.scheduled_date >= today).sort(chronological),
    earlierOpen: records.filter(item => isOpen(item) && item.scheduled_date < today).sort((a,b) => chronological(b,a)),
    history: records.filter(item => !isOpen(item)).sort((a,b) => chronological(b,a)),
  }
}

export function formatPortalDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return value
  const date = new Date(value + 'T12:00:00Z')
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0,10) !== value) return value
  return new Intl.DateTimeFormat('en-US', { weekday: 'short', month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(date)
}

export function formatPortalAppointment(item: Pick<PortalAppointmentSummary, 'scheduled_date' | 'start_time'>): string {
  const match = /^(\d{2}):(\d{2})(?::\d{2}(?:\.\d+)?)?$/.exec(item.start_time)
  if (!match || Number(match[1]) > 23 || Number(match[2]) > 59) return formatPortalDate(item.scheduled_date) + ' at ' + item.start_time
  const hours = Number(match[1])
  return formatPortalDate(item.scheduled_date) + ' at ' + (hours % 12 || 12) + ':' + match[2] + (hours >= 12 ? ' PM' : ' AM')
}
