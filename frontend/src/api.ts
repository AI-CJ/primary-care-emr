// The browser build never sends API requests over the network.
export const BROWSER_MODE = import.meta.env?.VITE_EMR_BROWSER === '1'
// An explicit empty value supports a same-origin reverse proxy.
export const API_BASE_URL = BROWSER_MODE
  ? 'http://emr.local'
  : (import.meta.env?.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/+$/, '')

type ApiValidationError = {
  msg?: string
}

type ApiErrorResponse = {
  detail?: string | ApiValidationError[]
}

export async function getApiErrorMessage(
  response: Response,
): Promise<string> {
  try {
    const data =
      (await response.json()) as ApiErrorResponse

    if (typeof data.detail === 'string') {
      return data.detail
    }

    if (Array.isArray(data.detail)) {
      const messages = data.detail
        .map((item) => item.msg)
        .filter(
          (message): message is string =>
            Boolean(message)
        )

      if (messages.length > 0) {
        return messages.join(' ')
      }
    }
  } catch {
    // Use the generic message below.
  }

  return `Request failed with status ${response.status}.`
}
let accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

// Keep the session in memory rather than persisting a bearer token in the browser.
export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers)
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  const response = BROWSER_MODE
    ? await (await import('./browserApi')).browserFetch(input, { ...init, headers })
    : await fetch(input, { ...init, headers })
  if (response.status === 401 && accessToken) {
    accessToken = null
    window.dispatchEvent(new Event('emr:session-ended'))
  }
  return response
}
