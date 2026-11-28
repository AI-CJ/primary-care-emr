// Clinical search text and record identifiers stay in the worker. Only these
// fixed, same-origin catalog assets can be fetched on demand.
export function referenceKindsFor(request) {
  const path = new URL(request.url).pathname
  const method = request.method.toUpperCase()
  const needed = new Set()
  if (method === 'POST') {
    if (path === '/diagnosis-codes/search') needed.add('icd10')
    const search = /^\/clinical-reference\/(rxnorm|cvx|mvx)\/search$/.exec(path)
    if (search) needed.add(search[1])
  }
  if (method === 'POST' || method === 'PUT') {
    let body
    try { body = JSON.parse(request.body || '{}') } catch { body = {} }
    if (/^\/(patients\/\d+\/problems|problems\/\d+)$/.test(path) && body?.icd10_code) needed.add('icd10')
    if (/^\/(patients\/\d+\/medications|medications\/\d+)$/.test(path) && body?.rxnorm_cui) needed.add('rxnorm')
    if (/^\/patients\/\d+\/immunizations$/.test(path)) {
      needed.add('cvx')
      if (body?.manufacturer_code) needed.add('mvx')
    }
  }
  return [...needed]
}

export function createReferenceLoader({ runtimeURL, fetchAsset = fetch }) {
  const loaded = new Set()
  return async (pyodide, request) => {
    for (const kind of referenceKindsFor(request)) {
      if (loaded.has(kind)) continue
      try {
        const response = await fetchAsset(new URL(kind + '.zip', runtimeURL))
        if (!response.ok) throw new Error('Catalog unavailable')
        pyodide.unpackArchive(await response.arrayBuffer(), 'zip')
        loaded.add(kind)
      } catch {
        // The authenticated API returns its normal unavailable-reference
        // response. A later request retries; failure is never cached as success.
      }
    }
  }
}
