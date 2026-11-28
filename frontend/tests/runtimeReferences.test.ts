import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createReferenceLoader, referenceKindsFor } from '../public/runtime-references.mjs'

const request = (method: string, path: string, body: unknown = {}) => ({
  method, url: 'http://emr.local' + path, body: JSON.stringify(body),
})

test('only reference lookup and coded writes load clinical catalogs', () => {
  for (const path of ['/auth/me', '/patients', '/patients/1/problems', '/worklists/counts', '/portal/problems']) {
    assert.deepEqual(referenceKindsFor(request('GET', path)), [])
  }
  assert.deepEqual(referenceKindsFor(request('POST', '/auth/login', { username: 'clinician' })), [])
  assert.deepEqual(referenceKindsFor(request('POST', '/diagnosis-codes/search', { query: 'hypertension' })), ['icd10'])
  assert.deepEqual(referenceKindsFor(request('POST', '/patients/1/problems', { icd10_code: 'I10' })), ['icd10'])
  assert.deepEqual(referenceKindsFor(request('PUT', '/problems/42', { icd10_code: 'E11.9' })), ['icd10'])
  assert.deepEqual(referenceKindsFor(request('PUT', '/problems/42', { icd10_code: null })), [])
  assert.deepEqual(referenceKindsFor(request('POST', '/patients/1/problems', { name: 'Uncoded record' })), [])
  for (const kind of ['rxnorm', 'cvx', 'mvx']) {
    assert.deepEqual(referenceKindsFor(request('POST', '/clinical-reference/' + kind + '/search')), [kind])
  }
  assert.deepEqual(referenceKindsFor(request('POST', '/clinical-reference/unknown/search')), [])
  assert.deepEqual(referenceKindsFor(request('POST', '/patients/1/immunizations', { manufacturer_code: 'PFZ' })), ['cvx', 'mvx'])
  assert.deepEqual(referenceKindsFor(request('PUT', '/medications/1', { rxnorm_cui: '123' })), ['rxnorm'])
})

test('catalog downloads use fixed asset URLs and successful loads are reused', async () => {
  const downloaded: string[] = []
  const unpacked: ArrayBuffer[] = []
  const bytes = new ArrayBuffer(4)
  const prepare = createReferenceLoader({
    runtimeURL: new URL('https://example.test/primary-care-emr/runtime/'),
    fetchAsset: async (url: URL) => {
      downloaded.push(url.href)
      return { ok: true, arrayBuffer: async () => bytes }
    },
  })
  const pyodide = { unpackArchive: (archive: ArrayBuffer, format: string) => {
    assert.equal(format, 'zip')
    unpacked.push(archive)
  } }
  await prepare(pyodide, request('GET', '/patients/123/problems'))
  assert.equal(downloaded.length, 0)
  await prepare(pyodide, request('POST', '/diagnosis-codes/search', { query: 'Private clinical text' }))
  await prepare(pyodide, request('PUT', '/problems/123', { icd10_code: 'I10' }))
  assert.deepEqual(downloaded, ['https://example.test/primary-care-emr/runtime/icd10.zip'])
  assert.deepEqual(unpacked, [bytes])
})

test('an unavailable or invalid archive can be retried on the next request', async () => {
  let attempts = 0
  let unpacks = 0
  const prepare = createReferenceLoader({
    runtimeURL: new URL('https://example.test/runtime/'),
    fetchAsset: async () => ({ ok: ++attempts > 1, arrayBuffer: async () => new ArrayBuffer(4) }),
  })
  const pyodide = { unpackArchive: () => {
    if (++unpacks === 1) throw new Error('Invalid archive')
  } }
  const lookup = request('POST', '/diagnosis-codes/search', { query: 'I10' })
  await prepare(pyodide, lookup)
  await prepare(pyodide, lookup)
  await prepare(pyodide, lookup)
  await prepare(pyodide, lookup)
  assert.equal(attempts, 3)
  assert.equal(unpacks, 2)
})
