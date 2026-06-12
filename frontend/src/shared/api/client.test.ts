import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, ApiError } from './client'
import { getAccessToken, getRefreshToken, saveTokens } from './tokens'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('apiFetch', () => {
  it('attaches the stored access token as Authorization', async () => {
    saveTokens({ access_token: 'acc-1', refresh_token: 'ref-1', token_type: 'bearer' })
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await apiFetch('/users/me/profile')

    const [, init] = fetchMock.mock.calls[0]
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer acc-1')
  })

  it('on 401 refreshes the pair and retries the request', async () => {
    saveTokens({ access_token: 'old-acc', refresh_token: 'old-ref', token_type: 'bearer' })
    const fetchMock = vi
      .fn()
      // 1) original request — 401
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
      // 2) POST /auth/refresh — new pair
      .mockResolvedValueOnce(
        jsonResponse(200, {
          access_token: 'new-acc',
          refresh_token: 'new-ref',
          token_type: 'bearer',
        }),
      )
      // 3) retried request — success
      .mockResolvedValueOnce(jsonResponse(200, { id: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await apiFetch<{ id: number }>('/users/me/profile')

    expect(result).toEqual({ id: 1 })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[1][0]).toBe('/api/auth/refresh')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ refresh_token: 'old-ref' })
    const retryHeaders = fetchMock.mock.calls[2][1].headers as Record<string, string>
    expect(retryHeaders.Authorization).toBe('Bearer new-acc')
    expect(getAccessToken()).toBe('new-acc')
    expect(getRefreshToken()).toBe('new-ref')
  })

  it('on 401 with a dead refresh clears tokens and throws ApiError(401)', async () => {
    saveTokens({ access_token: 'old-acc', refresh_token: 'dead-ref', token_type: 'bearer' })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }))
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'refresh invalid' }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiFetch('/users/me/profile')).rejects.toMatchObject({ status: 401 })
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })

  it('propagates the FastAPI error detail', async () => {
    // a Response body can be read once — return a fresh object per call
    const fetchMock = vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(jsonResponse(409, { detail: 'Login already taken.' })),
      )
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiFetch('/auth/register', { skipAuth: true })).rejects.toThrowError(
      ApiError,
    )
    await expect(
      apiFetch('/auth/register', { skipAuth: true }),
    ).rejects.toMatchObject({ status: 409, message: 'Login already taken.' })
  })

  it('returns undefined for 204 No Content', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    await expect(apiFetch('/posts/1/like', { method: 'DELETE' })).resolves.toBeUndefined()
  })
})
