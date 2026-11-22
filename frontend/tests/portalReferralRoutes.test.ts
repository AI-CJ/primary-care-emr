import assert from 'node:assert/strict'
import { test } from 'node:test'
import { portalReferralsPath } from '../src/portalReferralRoutes.ts'

test('signed-in patients request only session-scoped referrals', () => {
  assert.equal(portalReferralsPath(), '/portal/referrals')
  assert.equal(portalReferralsPath().includes('patients/'), false)
})

test('staff preview retains its separate chart-scoped referral endpoint', () => {
  assert.equal(portalReferralsPath(42), '/patients/42/portal-preview/referrals')
  assert.equal(portalReferralsPath(0), '/patients/0/portal-preview/referrals')
})
