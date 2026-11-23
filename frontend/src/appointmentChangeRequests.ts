import type { AppointmentChangeRequest, PortalAppointmentSummary } from './types'

// UI filtering is a convenience; the server enforces eligibility and uniqueness.
export function requestableAppointments(
  appointments: PortalAppointmentSummary[],
  requests: AppointmentChangeRequest[],
  today: string,
): PortalAppointmentSummary[] {
  const pendingIds = new Set(requests.filter((request) => request.status === 'pending')
    .map((request) => request.appointment_id))
  return appointments.filter((appointment) =>
    appointment.status === 'scheduled' &&
    appointment.scheduled_date >= today &&
    !pendingIds.has(appointment.id)
  ).sort((first, second) =>
    first.scheduled_date.localeCompare(second.scheduled_date) ||
    first.start_time.localeCompare(second.start_time) ||
    first.id - second.id)
}
