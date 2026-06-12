import type { InputHTMLAttributes } from 'react'
import { useId } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export function Input({ label, error, className, ...rest }: InputProps) {
  const id = useId()
  const inputClasses = ['input', error && 'input--error', className].filter(Boolean).join(' ')
  return (
    <div className="input-group">
      {label && <label htmlFor={id}>{label}</label>}
      <input id={id} className={inputClasses} {...rest} />
      {error && <span className="input-error-msg">{error}</span>}
    </div>
  )
}
