/* Pure validation functions; bounds mirror the backend RegisterIn/LoginIn. */

export interface LoginFormValues {
  login: string
  password: string
}

export interface RegisterFormValues {
  first_name: string
  last_name: string
  login: string
  password: string
}

export type FieldErrors<T> = Partial<Record<keyof T, string>>

export const LOGIN_MIN = 3
export const LOGIN_MAX = 32
export const PASSWORD_MIN = 8
export const PASSWORD_MAX = 128
export const NAME_MAX = 50

export function validateLogin(values: LoginFormValues): FieldErrors<LoginFormValues> {
  const errors: FieldErrors<LoginFormValues> = {}
  const login = values.login.trim()
  if (!login) errors.login = 'Введите логин'
  else if (login.length < LOGIN_MIN || login.length > LOGIN_MAX)
    errors.login = `Логин — от ${LOGIN_MIN} до ${LOGIN_MAX} символов`
  if (!values.password) errors.password = 'Введите пароль'
  return errors
}

export function validateRegister(values: RegisterFormValues): FieldErrors<RegisterFormValues> {
  const errors: FieldErrors<RegisterFormValues> = {}
  if (!values.first_name.trim()) errors.first_name = 'Введите имя'
  else if (values.first_name.trim().length > NAME_MAX)
    errors.first_name = `Имя — не длиннее ${NAME_MAX} символов`
  if (!values.last_name.trim()) errors.last_name = 'Введите фамилию'
  else if (values.last_name.trim().length > NAME_MAX)
    errors.last_name = `Фамилия — не длиннее ${NAME_MAX} символов`
  const login = values.login.trim()
  if (!login) errors.login = 'Введите логин'
  else if (login.length < LOGIN_MIN || login.length > LOGIN_MAX)
    errors.login = `Логин — от ${LOGIN_MIN} до ${LOGIN_MAX} символов`
  if (!values.password) errors.password = 'Введите пароль'
  else if (values.password.length < PASSWORD_MIN)
    errors.password = `Пароль — минимум ${PASSWORD_MIN} символов`
  else if (values.password.length > PASSWORD_MAX)
    errors.password = `Пароль — максимум ${PASSWORD_MAX} символов`
  return errors
}

export function hasErrors(errors: FieldErrors<object>): boolean {
  return Object.keys(errors).length > 0
}
