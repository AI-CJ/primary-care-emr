type Reply = { status: number; headers: [string, string][]; body: string }
type WorkerReply = { id: number; reply?: Reply; error?: string }
type Pending = {
  resolve: (reply: Reply) => void
  reject: (error: Error) => void
}

let worker: Worker | null = null
let nextId = 0
const pending = new Map<number, Pending>()

export function closeBrowserSession(): void {
  worker?.terminate()
  worker = null
  for (const entry of pending.values()) entry.reject(new Error('Workspace closed.'))
  pending.clear()
}

function getWorker(): Worker {
  if (worker) return worker
  worker = new Worker(new URL(import.meta.env.BASE_URL + 'runtime-worker.mjs', document.baseURI), {
    type: 'module',
  })
  worker.onmessage = (event: MessageEvent<WorkerReply>) => {
    const { id, reply, error } = event.data
    const entry = pending.get(id)
    if (!entry) return
    pending.delete(id)
    if (reply) entry.resolve(reply)
    else entry.reject(new Error(error ?? 'The workspace could not complete the request.'))
  }
  worker.onerror = () => closeBrowserSession()
  return worker
}

function headersFor(headers: Headers): [string, string][] {
  const values: [string, string][] = []
  headers.forEach((value, key) => values.push([key, value]))
  return values
}

export async function browserFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const request = new Request(input, init)
  if (new URL(request.url).origin !== 'http://emr.local') {
    throw new Error('The browser workspace cannot access external API origins.')
  }
  const body = request.body ? await request.text() : ''
  request.signal.throwIfAborted()
  const result = await new Promise<Reply>((resolve, reject) => {
    const id = ++nextId
    const abort = () => {
      pending.delete(id)
      reject(new DOMException('Request aborted', 'AbortError'))
    }
    pending.set(id, {
      resolve: (reply) => { request.signal.removeEventListener('abort', abort); resolve(reply) },
      reject: (error) => { request.signal.removeEventListener('abort', abort); reject(error) },
    })
    request.signal.addEventListener('abort', abort, { once: true })
    try {
      getWorker().postMessage({
        id,
        request: {
          url: request.url,
          method: request.method,
          headers: headersFor(request.headers),
          body,
        },
      })
    } catch (error) {
      pending.delete(id)
      request.signal.removeEventListener('abort', abort)
      reject(error)
    }
  })
  return new Response(result.status === 204 || result.status === 304 || result.status === 205
    ? null : result.body, { status: result.status, headers: result.headers })
}
