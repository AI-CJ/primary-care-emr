import { test } from 'node:test'
import assert from 'node:assert/strict'
import { groupPortalAppointments, formatPortalAppointment, formatPortalDate } from '../src/portalAppointments.ts'
import type { PortalAppointmentSummary } from '../src/types.ts'

function appointment(id: number, scheduled_date: string, status: PortalAppointmentSummary['status'], start_time = '09:00:00'): PortalAppointmentSummary {
  return { id, scheduled_date, status, start_time, reason_for_visit: 'Follow-up' }
}

test('future and same-day open visits, earlier unresolved appointments and closed history are mutually exclusive', () => {
  const records = [appointment(4, '2026-11-25', 'scheduled'), appointment(1, '2026-11-22', 'scheduled'),
    appointment(2, '2026-11-24', 'checked_in'), appointment(3, '2026-11-23', 'checked_in'),
    appointment(5, '2026-11-24', 'cancelled'), appointment(6, '2026-11-24', 'completed'),
    appointment(7, '2026-11-21', 'no_show'), appointment(8, '2026-11-25', 'scheduled', '08:00:00')]
  const result = groupPortalAppointments(records, '2026-11-24')
  assert.deepEqual(result.upcoming.map(item => item.id), [2,8,4])
  assert.deepEqual(result.earlierOpen.map(item => item.id), [3,1])
  assert.deepEqual(result.history.map(item => item.id), [6,5,7])
  assert.deepEqual(records.map(item => item.id), [4,1,2,3,5,6,7,8])
})

test('empty data does not manufacture an appointment', () => {
  assert.deepEqual(groupPortalAppointments([], '2026-11-24'), { upcoming: [], earlierOpen: [], history: [] })
})

test('format recorded calendar dates without day shifts and distinguish midnight from noon', () => {
  assert.equal(formatPortalDate('2026-11-24'), 'Tue, November 24, 2026')
  assert.equal(formatPortalAppointment({ scheduled_date:'2026-11-24', start_time:'00:05:00' }), 'Tue, November 24, 2026 at 12:05 AM')
  assert.equal(formatPortalAppointment({ scheduled_date:'2026-11-24', start_time:'12:30:00' }), 'Tue, November 24, 2026 at 12:30 PM')
  assert.equal(formatPortalDate('2026-02-30'), '2026-02-30')
})
