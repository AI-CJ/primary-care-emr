import assert from 'node:assert/strict'
import { test } from 'node:test'
import { portalVisitsPath } from '../src/portalVisitRoutes.ts'

test('signed-in patients request session-scoped finalized visits', () => {
  assert.equal(portalVisitsPath(), '/portal/visits')
  assert.equal(portalVisitsPath().includes('patient'), false)
})

test('staff preview retains a separate patient-chart scoped endpoint', () => {
  assert.equal(portalVisitsPath(42), '/patients/42/portal-preview/visits')
  assert.equal(portalVisitsPath(0), '/patients/0/portal-preview/visits')
})
