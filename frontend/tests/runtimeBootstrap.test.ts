import { test } from 'node:test'
import assert from 'node:assert/strict'
import { pbkdf2Sync, webcrypto } from 'node:crypto'
import { initializeRuntime, prepareDemoHashes } from '../public/runtime-bootstrap.mjs'

const runtimeURL = new URL('https://example.test/runtime/')

test('fetch the independent archive before Python core is ready, then initialize once', async () => {
  const events: string[] = []
  let releaseCore: () => void = () => { throw new Error('Core did not start') }
  const coreReady = new Promise<void>(resolve => { releaseCore = resolve })
  const archive = new ArrayBuffer(8)
  const runtime = {
    async loadPackage(packages: string[]) {
      assert.deepEqual(packages, ['fastapi', 'sqlalchemy', 'cryptography'])
      events.push('packages')
    },
    unpackArchive(bytes: ArrayBuffer, format: string) {
      assert.equal(bytes, archive)
      assert.equal(format, 'zip')
      events.push('unpack')
    },
    async runPythonAsync(source: string) { events.push(source) },
  }
  let report: Record<string, number> | undefined
  const initializing = initializeRuntime({
    runtimeURL,
    prepareHashes: async () => null,
    loadPyodide: async ({ indexURL }: { indexURL: string }) => {
      assert.equal(indexURL, runtimeURL.href)
      events.push('core')
      await coreReady
      return runtime
    },
    fetchAsset: async (url: URL) => {
      assert.equal(url.href, runtimeURL.href + 'backend.zip')
      events.push('archive')
      return { ok: true, arrayBuffer: async () => archive }
    },
    report: (timings: Record<string, number>) => { report = timings },
  })
  assert.deepEqual(events, ['core', 'archive'])
  releaseCore()
  assert.equal(await initializing, runtime)
  assert.deepEqual(events, ['core', 'archive', 'packages', 'unpack',
    'from backend.browser_demo import initialize_browser, browser_request',
    'initialize_browser()',
    'from backend.synthetic_population import extend_browser_population; extend_browser_population()',
    'from backend.main import app'])
  assert.ok(report)
  assert.deepEqual(Object.keys(report).sort(), ['apiImportMs', 'archiveDownloadMs', 'coreMs',
    'databaseSeedMs', 'demoPasswordSeedMs', 'packagesMs', 'populationSeedMs', 'pythonImportMs', 'totalMs', 'unpackMs'].sort())
  assert.ok(Object.values(report).every(value => Number.isFinite(value) && value >= 0))
})

test('a failed application archive prevents database initialization', async () => {
  let unpacked = false
  let reported = false
  await assert.rejects(initializeRuntime({
    runtimeURL,
    prepareHashes: async () => null,
    loadPyodide: async () => ({
      loadPackage: async () => {},
      unpackArchive: () => { unpacked = true },
      runPythonAsync: async () => { throw new Error('Unexpected Python execution') },
    }),
    fetchAsset: async () => ({ ok: false }),
    report: () => { reported = true },
  }), /Application package unavailable/)
  assert.equal(unpacked, false)
  assert.equal(reported, false)
})

test('native seed derives the exact Python password format with fresh per-account salts', async () => {
  const hashes = await prepareDemoHashes(webcrypto)
  assert.ok(hashes)
  assert.deepEqual(Object.keys(hashes).sort(), ['admin', 'clinician', 'jordan.lee', 'maria.thompson'])
  const salts = new Set<string>()
  for (const encoded of Object.values(hashes)) {
    const [scheme, rounds, salt, digest] = (encoded as string).split('$')
    assert.equal(scheme, 'pbkdf2_sha256')
    assert.equal(rounds, '600000')
    const saltBytes = Buffer.from(salt, 'base64url')
    assert.equal(saltBytes.length, 16)
    assert.deepEqual(Buffer.from(digest, 'base64url'),
      pbkdf2Sync('Welcome-EMR-2026', saltBytes, 600000, 32, 'sha256'))
    salts.add(salt)
  }
  assert.equal(salts.size, 4)
  assert.equal(await prepareDemoHashes({}), null)
})

test('native seed input is passed once to the browser initializer', async () => {
  const hashes = { admin: 'fixed-test-value' }
  const calls: string[] = []
  await initializeRuntime({
    runtimeURL,
    prepareHashes: async () => hashes,
    loadPyodide: async () => ({
      loadPackage: async () => {},
      unpackArchive: () => {},
      runPythonAsync: async (source: string) => { calls.push(source) },
    }),
    fetchAsset: async () => ({ ok: true, arrayBuffer: async () => new ArrayBuffer(0) }),
  })
  assert.equal(calls.filter(source => source.startsWith('initialize_browser(')).length, 1)
  assert.equal(calls[1], 'initialize_browser(' + JSON.stringify(JSON.stringify(hashes)) + ')')
})
