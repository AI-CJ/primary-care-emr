import { test } from 'node:test'
import assert from 'node:assert/strict'
import { groupPortalLabOrders } from '../src/portalLabGroups.ts'
import type { PortalLabOrder } from '../src/types.ts'

function order(id: number, status: PortalLabOrder['status'], released = false): PortalLabOrder {
  const day = '2026-11-' + String(id).padStart(2, '0')
  return { id, status, ordered_at: day + 'T10:00:00Z', cancelled_at: null, test_name: 'Test ' + id,
    result: released ? { collected_on: day, reported_at: day + 'T12:00:00Z', result_text: 'Clinic supplied text' } : null }
}

test('released results sort newest first without dropping earlier results', () => {
  const records = [order(1,'resulted',true),order(4,'resulted',true),order(2,'resulted',true),order(3,'resulted',true),order(5,'resulted',true)]
  const result = groupPortalLabOrders(records)
  assert.deepEqual(result.recent.map(item => item.id), [5,4,3])
  assert.deepEqual(result.older.map(item => item.id), [2,1])
  assert.deepEqual(records.map(item => item.id), [1,4,2,3,5])
})

test('only resulted orders with a returned result are classified as released', () => {
  const result = groupPortalLabOrders([order(1,'ordered',true),order(2,'resulted'),order(3,'cancelled',true),order(4,'resulted',true)])
  assert.deepEqual(result.recent.map(item => item.id), [4])
  assert.deepEqual(result.pending.map(item => item.id), [1])
  assert.deepEqual(result.awaitingRelease.map(item => item.id), [2])
  assert.deepEqual(result.cancelled.map(item => item.id), [3])
  assert.equal(result.older.length, 0)
})

test('empty list stays empty', () => {
  assert.deepEqual(groupPortalLabOrders([]), { recent: [], older: [], pending: [], awaitingRelease: [], cancelled: [] })
})
