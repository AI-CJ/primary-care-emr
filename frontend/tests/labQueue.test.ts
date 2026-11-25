import assert from 'node:assert/strict'
import { test } from 'node:test'
import { filterLabQueue, labQueuePage, LAB_PAGE_SIZE } from '../src/labQueue.ts'

const orders = Array.from({ length: 13 }, (_, index) => ({
  id: index + 1,
  patient_name: index % 2 ? 'Jordan Lee' : 'Maria Thompson',
  test_name: index % 3 ? 'Lipid panel' : 'Basic metabolic panel',
  priority: index < 3 ? 'urgent' as const : 'routine' as const,
}))

test('filters by patient, test, identifier and priority without reordering', () => {
  assert.deepEqual(filterLabQueue(orders, '  JORDAN lipid ', 'all').map(row => row.id), [2, 6, 8, 12])
  assert.deepEqual(filterLabQueue(orders, 'Jordan', 'urgent').map(row => row.id), [2])
  assert.deepEqual(filterLabQueue(orders, 'Maria 13', 'routine').map(row => row.id), [13])
  assert.deepEqual(filterLabQueue(orders, '', 'all'), orders)
  assert.deepEqual(filterLabQueue(orders, 'not present', 'all'), [])
})

test('pages contain at most six rows; boundaries remain valid after resolution', () => {
  const first = labQueuePage(orders, 0)
  assert.equal(first.rows.length, LAB_PAGE_SIZE)
  assert.equal(first.pages, 3)
  assert.deepEqual(labQueuePage(orders, 1).rows.map(row => row.id), [7, 8, 9, 10, 11, 12])
  assert.deepEqual(labQueuePage(orders, 2).rows.map(row => row.id), [13])
  const remaining = labQueuePage(orders.slice(0, 12), 2)
  assert.equal(remaining.page, 1)
  assert.equal(remaining.end, 12)
  assert.equal(labQueuePage(orders, -1).page, 0)
  assert.deepEqual(labQueuePage([], 4), { page: 0, pages: 1, start: 0, end: 0, rows: [] })
})
