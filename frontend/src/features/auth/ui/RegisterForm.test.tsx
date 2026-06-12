import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, afterEach } from 'vitest'
import { AuthProvider } from '../model/AuthContext'
import { RegisterForm } from './RegisterForm'

function renderForm() {
  const fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  render(
    <AuthProvider>
      <RegisterForm />
    </AuthProvider>,
  )
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('RegisterForm', () => {
  it('shows errors for an empty form without calling the API', async () => {
    const fetchMock = renderForm()
    await userEvent.click(screen.getByRole('button', { name: 'Зарегистрироваться' }))

    expect(screen.getByText('Введите имя')).toBeInTheDocument()
    expect(screen.getByText('Введите фамилию')).toBeInTheDocument()
    expect(screen.getByText('Введите логин')).toBeInTheDocument()
    expect(screen.getByText('Введите пароль')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('rejects a short password without calling the API', async () => {
    const fetchMock = renderForm()
    await userEvent.type(screen.getByLabelText('Имя'), 'Тим')
    await userEvent.type(screen.getByLabelText('Фамилия'), 'Д')
    await userEvent.type(screen.getByLabelText('Логин'), 'tim_d')
    await userEvent.type(screen.getByLabelText('Пароль'), '1234567')
    await userEvent.click(screen.getByRole('button', { name: 'Зарегистрироваться' }))

    expect(screen.getByText(/минимум 8 символов/)).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('submits valid values to POST /api/auth/register', async () => {
    const fetchMock = renderForm()
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 }),
    )
    await userEvent.type(screen.getByLabelText('Имя'), 'Тим')
    await userEvent.type(screen.getByLabelText('Фамилия'), 'Д')
    await userEvent.type(screen.getByLabelText('Логин'), 'tim_d')
    await userEvent.type(screen.getByLabelText('Пароль'), 'verysecure8')
    await userEvent.click(screen.getByRole('button', { name: 'Зарегистрироваться' }))

    expect(fetchMock).toHaveBeenCalled()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/auth/register')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toMatchObject({
      first_name: 'Тим',
      login: 'tim_d',
    })
  })
})
