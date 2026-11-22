import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { PortalCareGoalSummary } from '../src/types.ts'
import { groupPortalCareGoals } from '../src/portalCareGoalGroups.ts'

function goal(
  id: number,
  status: PortalCareGoalSummary['status'],
  target_date: string | null = null,
  completed_at: string | null = null,
  discontinued_at: string | null = null,
): PortalCareGoalSummary {
  return {
    id,
    title: `Synthetic goal ${id}`,
    status,
    target_date,
    created_at: '2026-11-01T10:00:00Z',
    completed_at,
    discontinued_at,
  }
}

test('active goals are ordered by target date, with undated goals last', () => {
  const input = [
    goal(4, 'active'),
    goal(3, 'active', '2027-03-01'),
    goal(2, 'active', '2027-01-01'),
    goal(1, 'active', '2027-01-01'),
  ]
  assert.deepEqual(groupPortalCareGoals(input).active.map((item) => item.id), [1, 2, 3, 4])
})

test('completed and discontinued goals appear in reverse closure order', () => {
  const input = [
    goal(1, 'completed', null, '2026-11-04T10:00:00Z'),
    goal(2, 'discontinued', null, null, '2026-11-07T10:00:00Z'),
    goal(3, 'completed', null, '2026-11-07T10:00:00Z'),
    goal(4, 'active'),
  ]
  const { active, past } = groupPortalCareGoals(input)
  assert.deepEqual(active.map((item) => item.id), [4])
  assert.deepEqual(past.map((item) => item.id), [3, 2, 1])
  assert.deepEqual(past.map((item) => item.status), ['completed', 'discontinued', 'completed'])
})

test('missing closure dates fall back to creation date, without modifying input', () => {
  const input = [goal(4, 'discontinued'), goal(2, 'completed'), goal(5, 'active')]
  const before = structuredClone(input)
  const grouped = groupPortalCareGoals(input)
  assert.deepEqual(grouped.past.map((item) => item.id), [4, 2])
  assert.deepEqual(input, before)
})

test('empty records keep both groups empty', () => {
  assert.deepEqual(groupPortalCareGoals([]), { active: [], past: [] })
})
