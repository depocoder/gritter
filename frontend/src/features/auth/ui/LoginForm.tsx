import { useState, type FormEvent } from 'react'
import { Button, Input } from '@/shared/ui'
import { ApiError } from '@/shared/api'
import { useAuth } from '../model/useAuth'
import {
  hasErrors,
  validateLogin,
  type FieldErrors,
  type LoginFormValues,
} from '../lib/validation'

export function LoginForm() {
  const { login } = useAuth()
  const [values, setValues] = useState<LoginFormValues>({ login: '', password: '' })
  const [errors, setErrors] = useState<FieldErrors<LoginFormValues>>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const validation = validateLogin(values)
    setErrors(validation)
    setServerError(null)
    if (hasErrors(validation)) return
    setSubmitting(true)
    try {
      await login(values)
    } catch (error) {
      setServerError(error instanceof ApiError ? error.message : 'Не удалось войти')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Форма входа">
      <div className="form-group">
        <Input
          label="Логин"
          placeholder="Введите логин"
          value={values.login}
          error={errors.login}
          onChange={(e) => setValues((v) => ({ ...v, login: e.target.value }))}
        />
      </div>
      <div className="form-group">
        <Input
          label="Пароль"
          type="password"
          placeholder="••••••"
          value={values.password}
          error={errors.password}
          onChange={(e) => setValues((v) => ({ ...v, password: e.target.value }))}
        />
      </div>
      {serverError && <p className="input-error-msg">{serverError}</p>}
      <div className="flex-row" style={{ justifyContent: 'space-between', marginTop: '1rem' }}>
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Входим…' : 'Войти'}
        </Button>
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault()
            alert('Инструкция по восстановлению отправлена на почту (демо)')
          }}
        >
          Не помню пароль
        </a>
      </div>
    </form>
  )
}
