import { test } from 'node:test'
import assert from 'node:assert/strict'
import { cleanEntryUrl } from '../src/entryUrl.ts'

test('remove marketing parameters while retaining the application path, other query values and fragment', () => {
  assert.equal(cleanEntryUrl('https://example.org/emr/?utm_source=external&view=chart&UTM_medium=link#section'),
    'https://example.org/emr/?view=chart#section')
  assert.equal(cleanEntryUrl('https://example.org/emr/?view=chart'), 'https://example.org/emr/?view=chart')
  assert.equal(cleanEntryUrl('https://example.org/emr/?utm_source=one&utm_source=two'), 'https://example.org/emr/')
})
