import assert from 'node:assert/strict'
import { test } from 'node:test'
import { requestableAppointments } from '../src/appointmentChangeRequests.ts'
import type { PortalAppointmentSummary, AppointmentChangeRequest } from '../src/types.ts'

function appt(id: number, date: string, status: PortalAppointmentSummary['status'] = 'scheduled'): PortalAppointmentSummary {
  return { id, scheduled_date: date, start_time: '10:00:00', reason_for_visit: 'Demo visit', status }
}
function request(appointment_id: number, status: AppointmentChangeRequest['status']): AppointmentChangeRequest {
  return { id: appointment_id + 100, appointment_id, kind: 'cancel', status,
    created_at: '2026-11-23T10:00:00Z', reviewed_at: null }
}

test('only current or future scheduled appointments are eligible', () => {
  assert.deepEqual(requestableAppointments([
    appt(1, '2026-11-22'), appt(2, '2026-11-23'), appt(3, '2026-11-24', 'checked_in'),
    appt(4, '2026-11-24', 'completed'), appt(5, '2026-11-25'),
  ], [], '2026-11-23').map((item) => item.id), [2, 5])
})
test('pending requests block duplicates, reviewed requests do not', () => {
  assert.deepEqual(requestableAppointments([
    appt(1, '2026-11-24'), appt(2, '2026-11-25'),
  ], [request(1, 'pending'), request(2, 'reviewed')], '2026-11-23')
    .map((item) => item.id), [2])
})
test('eligible appointments sort by date, time, and ID', () => {
  assert.deepEqual(requestableAppointments([
    { ...appt(3, '2026-11-24'), start_time: '11:00:00' },
    { ...appt(2, '2026-11-24'), start_time: '09:00:00' },
    { ...appt(1, '2026-11-24'), start_time: '09:00:00' },
  ], [], '2026-11-23').map((item) => item.id), [1, 2, 3])
})
