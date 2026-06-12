import { createContext } from 'react'
import type { User } from '@/entities/user'
import type { LoginFormValues, RegisterFormValues } from '../lib/validation'

export interface AuthContextValue {
  user: User | null
  /** true while the stored session is being validated on startup */
  initializing: boolean
  login: (values: LoginFormValues) => Promise<void>
  register: (values: RegisterFormValues) => Promise<void>
  logout: () => void
  setUser: (user: User) => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
