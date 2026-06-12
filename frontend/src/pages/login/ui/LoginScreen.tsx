import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { LoginForm, RegisterForm, useAuth } from '@/features/auth'
import { Spinner } from '@/shared/ui'

type Tab = 'login' | 'register'

export function LoginScreen() {
  const { user, initializing } = useAuth()
  const [tab, setTab] = useState<Tab>('login')

  if (initializing) return <Spinner />
  if (user) return <Navigate to="/feed" replace />

  return (
    <div className="auth-layout">
      <div className="auth-card">
        <div className="auth-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={tab === 'login'}
            className={`auth-tab ${tab === 'login' ? 'active' : ''}`}
            onClick={() => setTab('login')}
          >
            Вход
          </button>
          <button
            role="tab"
            aria-selected={tab === 'register'}
            className={`auth-tab ${tab === 'register' ? 'active' : ''}`}
            onClick={() => setTab('register')}
          >
            Регистрация
          </button>
        </div>
        {tab === 'login' ? <LoginForm /> : <RegisterForm />}
        <div className="auth-footer">Gritter — учебная социальная сеть</div>
      </div>
    </div>
  )
}
