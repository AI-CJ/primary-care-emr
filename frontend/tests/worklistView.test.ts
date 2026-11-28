import assert from 'node:assert/strict'
import { test } from 'node:test'
import { filterWorklist, worklistPage } from '../src/worklistView.ts'

const records = Array.from({ length: 15 }, (_, index) => ({
  id: index + 1,
  patient: index % 2 ? 'Jordan Lee' : 'Maria Thompson',
  title: index % 3 ? 'Review readings' : 'Schedule follow-up',
}))
const searchText = (row: typeof records[number]) => `${row.patient} ${row.title} ${row.id}`

test('search finds records beyond the visible page without changing clinical order', () => {
  const matches = filterWorklist(records, '  JORDAN   review ', searchText)
  assert.deepEqual(matches.map(row => row.id), [2, 6, 8, 12, 14])
  assert.deepEqual(filterWorklist(records, 'Maria 15', searchText).map(row => row.id), [15])
  assert.deepEqual(filterWorklist(records, 'not in this queue', searchText), [])
  assert.deepEqual(filterWorklist(records, ' ', searchText), records)
})

test('every record remains reachable and a refreshed shorter queue clamps the page', () => {
  const first = worklistPage(records, 0)
  const second = worklistPage(records, 1)
  const third = worklistPage(records, 2)
  assert.deepEqual([...first.rows, ...second.rows, ...third.rows], records)
  assert.equal(first.rows.length, 6)
  assert.equal(second.rows.length, 6)
  assert.equal(third.rows.length, 3)
  const refreshed = worklistPage(records.slice(0, 7), third.page)
  assert.equal(refreshed.page, 1)
  assert.equal(refreshed.start, 6)
  assert.equal(refreshed.end, 7)
  assert.deepEqual(refreshed.rows.map(row => row.id), [7])
  assert.deepEqual(worklistPage([], 9), { page: 0, pages: 1, start: 0, end: 0, rows: [] })
})
