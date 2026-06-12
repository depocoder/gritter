import { apiFetch, type TokenPair } from '@/shared/api'
import type { User } from '@/entities/user'
import type { LoginFormValues, RegisterFormValues } from '../lib/validation'

export function registerRequest(values: RegisterFormValues): Promise<User> {
  return apiFetch<User>('/auth/register', { method: 'POST', body: values, skipAuth: true })
}

export function loginRequest(values: LoginFormValues): Promise<TokenPair> {
  return apiFetch<TokenPair>('/auth/login', { method: 'POST', body: values, skipAuth: true })
}

export function changePasswordRequest(oldPassword: string, newPassword: string): Promise<void> {
  return apiFetch<void>('/auth/change-password', {
    method: 'POST',
    body: { old_password: oldPassword, new_password: newPassword },
  })
}
