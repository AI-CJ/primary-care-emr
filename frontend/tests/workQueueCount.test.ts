import { test } from 'node:test'
import assert from 'node:assert/strict'
import { formatWorkQueueCount } from '../src/workQueueCount.ts'

test('work queue counts do not imply a complete count at a server limit', () => {
  assert.equal(formatWorkQueueCount(0, 100), '0')
  assert.equal(formatWorkQueueCount(99, 100), '99')
  assert.equal(formatWorkQueueCount(100, 100), '100+')
  assert.equal(formatWorkQueueCount(105), '105')
})
