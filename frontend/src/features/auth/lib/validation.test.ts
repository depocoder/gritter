import { describe, expect, it } from 'vitest'
import {
  hasErrors,
  validateLogin,
  validateRegister,
  LOGIN_MIN,
  PASSWORD_MIN,
} from './validation'

const validRegister = {
  first_name: 'Тим',
  last_name: 'Добрынченко',
  login: 'tim_d',
  password: 'longenough8',
}

describe('validateRegister', () => {
  it('accepts valid values', () => {
    expect(validateRegister(validRegister)).toEqual({})
  })

  it('requires every field', () => {
    const errors = validateRegister({ first_name: '', last_name: '', login: '', password: '' })
    expect(errors.first_name).toBeTruthy()
    expect(errors.last_name).toBeTruthy()
    expect(errors.login).toBeTruthy()
    expect(errors.password).toBeTruthy()
  })

  it('rejects a 7-char password (boundary)', () => {
    const errors = validateRegister({ ...validRegister, password: '1234567' })
    expect(errors.password).toContain(String(PASSWORD_MIN))
  })

  it('accepts an 8-char password (boundary)', () => {
    expect(validateRegister({ ...validRegister, password: '12345678' })).toEqual({})
  })

  it('rejects a 2-char login and accepts a 3-char one (boundary)', () => {
    expect(validateRegister({ ...validRegister, login: 'ab' }).login).toContain(
      String(LOGIN_MIN),
    )
    expect(validateRegister({ ...validRegister, login: 'abc' })).toEqual({})
  })

  it('rejects a 33-char login (boundary)', () => {
    expect(validateRegister({ ...validRegister, login: 'a'.repeat(33) }).login).toBeTruthy()
  })

  it('treats whitespace-only names as empty', () => {
    expect(validateRegister({ ...validRegister, first_name: '   ' }).first_name).toBeTruthy()
  })
})

describe('validateLogin', () => {
  it('accepts valid values', () => {
    expect(validateLogin({ login: 'tim_d', password: 'x' })).toEqual({})
  })

  it('requires login and password', () => {
    const errors = validateLogin({ login: '', password: '' })
    expect(errors.login).toBeTruthy()
    expect(errors.password).toBeTruthy()
  })
})

describe('hasErrors', () => {
  it('distinguishes empty and non-empty results', () => {
    expect(hasErrors({})).toBe(false)
    expect(hasErrors({ login: 'err' })).toBe(true)
  })
})
