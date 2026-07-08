const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

/** Thrown for any non-2xx response; `detail` mirrors FastAPI's `{"detail": "..."}` body. */
export class ApiError extends Error {
  status: number

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * Thin fetch wrapper for the backend API. Always sends cookies (the
 * `session_uuid` auth cookie is httponly, so it can't be attached manually)
 * and resolves to the parsed JSON body, or rejects with `ApiError`.
 */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.detail ?? response.statusText)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

/** Builds a URL for an asset served from the backend's `/assets` static mount, given an `Image.filepath`. */
export function assetUrl(filepath: string): string {
  return `${API_BASE_URL}/assets/${filepath}`
}
