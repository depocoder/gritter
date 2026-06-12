import { useState, type FormEvent } from 'react'
import { Button, Input } from '@/shared/ui'
import { ApiError } from '@/shared/api'
import { useAuth } from '../model/useAuth'
import {
  hasErrors,
  validateRegister,
  type FieldErrors,
  type RegisterFormValues,
} from '../lib/validation'

const EMPTY: RegisterFormValues = { first_name: '', last_name: '', login: '', password: '' }

export function RegisterForm() {
  const { register } = useAuth()
  const [values, setValues] = useState<RegisterFormValues>(EMPTY)
  const [errors, setErrors] = useState<FieldErrors<RegisterFormValues>>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const setField = (field: keyof RegisterFormValues) => (value: string) =>
    setValues((v) => ({ ...v, [field]: value }))

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const validation = validateRegister(values)
    setErrors(validation)
    setServerError(null)
    if (hasErrors(validation)) return
    setSubmitting(true)
    try {
      await register(values)
    } catch (error) {
      setServerError(
        error instanceof ApiError ? error.message : 'Не удалось зарегистрироваться',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Форма регистрации">
      <div className="form-group">
        <Input
          label="Имя"
          placeholder="Алексей"
          value={values.first_name}
          error={errors.first_name}
          onChange={(e) => setField('first_name')(e.target.value)}
        />
      </div>
      <div className="form-group">
        <Input
          label="Фамилия"
          placeholder="Смирнов"
          value={values.last_name}
          error={errors.last_name}
          onChange={(e) => setField('last_name')(e.target.value)}
        />
      </div>
      <div className="form-group">
        <Input
          label="Логин"
          placeholder="alex_smirnov"
          value={values.login}
          error={errors.login}
          onChange={(e) => setField('login')(e.target.value)}
        />
      </div>
      <div className="form-group">
        <Input
          label="Пароль"
          type="password"
          placeholder="••••••"
          value={values.password}
          error={errors.password}
          onChange={(e) => setField('password')(e.target.value)}
        />
      </div>
      {serverError && <p className="input-error-msg">{serverError}</p>}
      <Button type="submit" style={{ width: '100%', marginTop: '0.5rem' }} disabled={submitting}>
        {submitting ? 'Создаём аккаунт…' : 'Зарегистрироваться'}
      </Button>
    </form>
  )
}
