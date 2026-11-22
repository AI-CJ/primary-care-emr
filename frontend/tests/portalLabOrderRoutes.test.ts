import assert from 'node:assert/strict'
import { test } from 'node:test'
import { portalLabOrdersPath } from '../src/portalLabOrderRoutes.ts'

test('signed-in patients request only session-scoped lab orders', () => {
  assert.equal(portalLabOrdersPath(), '/portal/lab-orders')
  assert.equal(portalLabOrdersPath().includes('patients/'), false)
})

test('staff preview retains its separate chart-scoped lab endpoint', () => {
  assert.equal(portalLabOrdersPath(42), '/patients/42/portal-preview/lab-orders')
  assert.equal(portalLabOrdersPath(0), '/patients/0/portal-preview/lab-orders')
})
