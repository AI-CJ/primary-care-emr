export const API_BASE_URL = 'http://127.0.0.1:8000'

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