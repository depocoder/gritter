/* On startup, fetching the profile doubles as a token-liveness check:
   a stale access token gets refreshed by apiFetch, a dead pair logs out. */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { clearTokens, getAccessToken, saveTokens, setSessionExpiredHandler } from '@/shared/api'
import { getMyProfile, type User } from '@/entities/user'
import { loginRequest, registerRequest } from '../api/authApi'
import type { LoginFormValues, RegisterFormValues } from '../lib/validation'
import { AuthContext } from './context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [initializing, setInitializing] = useState(() => getAccessToken() !== null)

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null))
    return () => setSessionExpiredHandler(null)
  }, [])

  useEffect(() => {
    if (!getAccessToken()) return
    getMyProfile()
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setInitializing(false))
  }, [])

  const login = useCallback(async (values: LoginFormValues) => {
    const pair = await loginRequest(values)
    saveTokens(pair)
    setUser(await getMyProfile())
  }, [])

  const register = useCallback(
    async (values: RegisterFormValues) => {
      await registerRequest(values)
      // registration does not return tokens — log in right away
      await login({ login: values.login, password: values.password })
    },
    [login],
  )

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, initializing, login, register, logout, setUser }),
    [user, initializing, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
