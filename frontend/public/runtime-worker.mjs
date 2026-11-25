import { loadPyodide } from './runtime/pyodide.mjs'
import { initializeRuntime } from './runtime-bootstrap.mjs'

let runtimePromise
let queue = Promise.resolve()

function initialize() {
  return initializeRuntime({
    loadPyodide,
    runtimeURL: new URL('./runtime/', import.meta.url),
    // Numeric stage timings only; never include credentials or chart data.
    report: timings => console.info('EMR startup ' + JSON.stringify(timings)),
  })
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
