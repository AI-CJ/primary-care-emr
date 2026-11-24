import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  canManagePatientLifecycle,
  nextPatientLifecycleAction,
  patientLifecycleStatus,
} from '../src/patientLifecycle.ts'

test('only administrator staff accounts can change lifecycle status', () => {
  assert.equal(canManagePatientLifecycle(null), false)
  assert.equal(canManagePatientLifecycle({ account_type: 'patient', staff_role: null }), false)
  assert.equal(canManagePatientLifecycle({ account_type: 'staff', staff_role: 'clinician' }), false)
  assert.equal(canManagePatientLifecycle({ account_type: 'staff', staff_role: 'admin' }), true)
})

test('active charts offer archive and archived charts offer reactivation', () => {
  assert.equal(patientLifecycleStatus(null), 'active')
  assert.equal(nextPatientLifecycleAction(null), 'archive')
  assert.equal(patientLifecycleStatus('2026-11-24T12:00:00Z'), 'archived')
  assert.equal(nextPatientLifecycleAction('2026-11-24T12:00:00Z'), 'reactivate')
})
