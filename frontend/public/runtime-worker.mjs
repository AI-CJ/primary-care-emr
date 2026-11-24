import { loadPyodide } from './runtime/pyodide.mjs'

let runtimePromise
let queue = Promise.resolve()

async function initialize() {
  const pyodide = await loadPyodide({ indexURL: new URL('./runtime/', import.meta.url).href })
  await pyodide.loadPackage(['fastapi', 'sqlalchemy', 'cryptography'])
  const response = await fetch(new URL('./runtime/backend.zip', import.meta.url))
  if (!response.ok) throw new Error('Application package unavailable')
  pyodide.unpackArchive(await response.arrayBuffer(), 'zip')
  await pyodide.runPythonAsync(`
from backend.browser_demo import initialize_browser, browser_request
initialize_browser()
from backend.main import app
`)
  return pyodide
}

// One database and one request queue per tab; no request is sent to a server.
self.onmessage = ({ data: { id, request } }) => {
  queue = queue.then(async () => {
    try {
      runtimePromise ??= initialize()
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
