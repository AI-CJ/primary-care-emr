// Only the four deliberately public demo identities use this seed path.
// Fresh independent salts for each worker; normal Python login verification is unchanged.
export async function prepareDemoHashes(provider = globalThis.crypto) {
  if (!provider?.subtle || typeof provider.getRandomValues !== 'function') return null
  try {
    const key = await provider.subtle.importKey(
      'raw', new TextEncoder().encode('Welcome-EMR-2026'), 'PBKDF2', false, ['deriveBits'],
    )
    const identities = ['admin', 'clinician', 'jordan.lee', 'maria.thompson']
    const base64url = bytes => btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_')
    const entries = await Promise.all(identities.map(async username => {
      const salt = provider.getRandomValues(new Uint8Array(16))
      const digest = new Uint8Array(await provider.subtle.deriveBits({
        name: 'PBKDF2', hash: 'SHA-256', salt, iterations: 600000,
      }, key, 256))
      return [username, 'pbkdf2_sha256$600000$' + base64url(salt) + '$' + base64url(digest)]
    }))
    return Object.fromEntries(entries)
  } catch {
    // Unsupported native crypto must not prevent ordinary Python seeding.
    return null
  }
}

// The backend archive is independent of the Python runtime download and setup.
// Keep all execution and clinical state inside the dedicated worker.
export async function initializeRuntime({ loadPyodide, runtimeURL, fetchAsset = fetch,
  now = () => performance.now(), report = () => {}, prepareHashes = prepareDemoHashes }) {
  const started = now()
  const timings = {}

  async function measure(name, action) {
    const start = now()
    const result = await action()
    timings[name] = Math.round(now() - start)
    return result
  }

  async function preparePython() {
    const pyodide = await measure('coreMs', () => loadPyodide({ indexURL: runtimeURL.href }))
    await measure('packagesMs', () => pyodide.loadPackage(['fastapi', 'sqlalchemy', 'cryptography']))
    return pyodide
  }

  async function downloadBackend() {
    return measure('archiveDownloadMs', async () => {
      const response = await fetchAsset(new URL('backend.zip', runtimeURL))
      if (!response.ok) throw new Error('Application package unavailable')
      return response.arrayBuffer()
    })
  }

  // Attach rejection handlers to both operations immediately. A failed asset
  // cannot result in a partially initialized workspace being returned.
  const [pyodide, archive, hashes] = await Promise.all([
    preparePython(), downloadBackend(), measure('demoPasswordSeedMs', prepareHashes),
  ])
  await measure('unpackMs', () => pyodide.unpackArchive(archive, 'zip'))
  await measure('pythonImportMs', () => pyodide.runPythonAsync(
    'from backend.browser_demo import initialize_browser, browser_request'))
  const seedSource = hashes === null ? 'initialize_browser()'
    : 'initialize_browser(' + JSON.stringify(JSON.stringify(hashes)) + ')'
  await measure('databaseSeedMs', () => pyodide.runPythonAsync(seedSource))
  await measure('populationSeedMs', () => pyodide.runPythonAsync(
    'from backend.synthetic_population import extend_browser_population; extend_browser_population()'))
  await measure('apiImportMs', () => pyodide.runPythonAsync('from backend.main import app'))
  timings.totalMs = Math.round(now() - started)
  report(timings)
  return pyodide
}
