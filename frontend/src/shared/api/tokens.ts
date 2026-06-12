/* JWT pair storage. localStorage survives reloads; the XSS trade-off is
   acceptable for this project and documented in the README. */

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

const ACCESS_KEY = 'gritter_access'
const REFRESH_KEY = 'gritter_refresh'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}

export function saveTokens(pair: TokenPair): void {
  localStorage.setItem(ACCESS_KEY, pair.access_token)
  localStorage.setItem(REFRESH_KEY, pair.refresh_token)
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}
