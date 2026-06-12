/* HTTP client over fetch: attaches the Bearer token, transparently refreshes
   the pair once on 401 and retries, normalizes errors into ApiError. */

import { API_BASE } from '@/shared/config'
import {
  type TokenPair,
  clearTokens,
  getAccessToken,
  getRefreshToken,
  saveTokens,
} from './tokens'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** AuthProvider subscribes to reset the user when the refresh token dies. */
let onSessionExpired: (() => void) | null = null
export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler
}

/* Refresh tokens are single-use, so concurrent 401s must share one refresh
   request: the first caller starts it, the rest await the same promise. */
let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false
  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!response.ok) return false
    const pair = (await response.json()) as TokenPair
    saveTokens(pair)
    return true
  } catch {
    return false
  }
}

function extractDetail(body: unknown): string | null {
  if (typeof body !== 'object' || body === null) return null
  const detail = (body as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    // FastAPI 422 returns [{loc, msg, type}, ...]
    return detail
      .map((item) => (typeof item?.msg === 'string' ? item.msg : ''))
      .filter(Boolean)
      .join('; ')
  }
  return null
}

export interface RequestOptions {
  method?: string
  body?: unknown
  /** Multipart uploads: skips JSON serialization and Content-Type */
  formData?: FormData
  /** Endpoints that work without auth (login/register) */
  skipAuth?: boolean
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, formData, skipAuth = false } = options

  const doFetch = (): Promise<Response> => {
    const headers: Record<string, string> = {}
    if (!skipAuth) {
      const token = getAccessToken()
      if (token) headers.Authorization = `Bearer ${token}`
    }
    let requestBody: BodyInit | undefined
    if (formData) {
      requestBody = formData
    } else if (body !== undefined) {
      headers['Content-Type'] = 'application/json'
      requestBody = JSON.stringify(body)
    }
    return fetch(`${API_BASE}${path}`, { method, headers, body: requestBody })
  }

  let response = await doFetch()

  if (response.status === 401 && !skipAuth) {
    refreshPromise = refreshPromise ?? tryRefresh().finally(() => {
      refreshPromise = null
    })
    const refreshed = await refreshPromise
    if (!refreshed) {
      clearTokens()
      onSessionExpired?.()
      throw new ApiError(401, 'Сессия истекла, войдите заново')
    }
    response = await doFetch()
  }

  if (!response.ok) {
    let message = `Ошибка запроса (${response.status})`
    try {
      const detail = extractDetail(await response.json())
      if (detail) message = detail
    } catch {
      // non-JSON body — keep the default message
    }
    throw new ApiError(response.status, message)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
