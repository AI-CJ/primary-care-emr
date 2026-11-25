import { loadPyodide } from './runtime/pyodide.mjs'
import { initializeRuntime } from './runtime-bootstrap.mjs'

let runtimePromise
let queue = Promise.resolve()
const loadedReferences = new Set()

function initialize() {
  return initializeRuntime({
    loadPyodide,
    runtimeURL: new URL('./runtime/', import.meta.url),
    // Numeric stage timings only; never include credentials or chart data.
    report: timings => console.info('EMR startup ' + JSON.stringify(timings)),
  })
}

async function prepareReferences(pyodide, request) {
  const path = new URL(request.url).pathname
  const search = /^\/clinical-reference\/(rxnorm|cvx|mvx)\/search$/.exec(path)
  const needed = new Set(search ? [search[1]] : [])
  if (request.method === 'POST' || request.method === 'PUT') {
    let body
    try { body = JSON.parse(request.body || '{}') } catch { body = {} }
    if (/^\/(patients\/\d+\/medications|medications\/\d+)$/.test(path) && body?.rxnorm_cui) needed.add('rxnorm')
    if (/^\/patients\/\d+\/immunizations$/.test(path)) {
      needed.add('cvx')
      if (body?.manufacturer_code) needed.add('mvx')
    }
  }
  for (const kind of needed) {
    if (loadedReferences.has(kind)) continue
    try {
      // Only constant same-origin asset URLs, never a clinical query or patient ID.
      const response = await fetch(new URL('./runtime/' + kind + '.zip', import.meta.url))
      if (!response.ok) throw new Error('Catalog unavailable')
      pyodide.unpackArchive(await response.arrayBuffer(), 'zip')
      loadedReferences.add(kind)
    } catch {
      // The authenticated API returns its normal unavailable-reference response.
      // Retrying a failed lookup can attempt the download again.
    }
  }
}

// One database and one request queue per tab; no request is sent to a server.
self.onmessage = ({ data: { id, request } }) => {
  queue = queue.then(async () => {
    try {
      runtimePromise ??= initialize().catch((error) => {
        // Startup errors contain no user-entered records.
        console.error('Workspace initialization failed:', String(error))
        throw error
      })
      const pyodide = await runtimePromise
      await prepareReferences(pyodide, request)
      pyodide.globals.set('request_json', JSON.stringify(request))
      const reply = JSON.parse(await pyodide.runPythonAsync('await browser_request(request_json)'))
      pyodide.globals.delete('request_json')
      self.postMessage({ id, reply })
    } catch (error) {
      // Log only the exception class. Do not log request or patient data.
      console.error('Workspace request failed:', error.name)
      self.postMessage({ id, error: 'The workspace could not complete the request. Reset and try again.' })
    }
  })
}
