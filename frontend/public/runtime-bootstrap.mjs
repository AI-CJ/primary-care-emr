// The backend archive is independent of the Python runtime download and setup.
// Keep all execution and clinical state inside the dedicated worker.
export async function initializeRuntime({ loadPyodide, runtimeURL, fetchAsset = fetch,
  now = () => performance.now(), report = () => {} }) {
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
  const [pyodide, archive] = await Promise.all([preparePython(), downloadBackend()])
  await measure('unpackMs', () => pyodide.unpackArchive(archive, 'zip'))
  await measure('pythonImportMs', () => pyodide.runPythonAsync(
    'from backend.browser_demo import initialize_browser, browser_request'))
  await measure('databaseSeedMs', () => pyodide.runPythonAsync('initialize_browser()'))
  await measure('populationSeedMs', () => pyodide.runPythonAsync(
    'from backend.synthetic_population import extend_browser_population; extend_browser_population()'))
  await measure('apiImportMs', () => pyodide.runPythonAsync('from backend.main import app'))
  timings.totalMs = Math.round(now() - started)
  report(timings)
  return pyodide
}
