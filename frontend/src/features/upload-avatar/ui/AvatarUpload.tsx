/* MIME/size limits mirror the backend avatar endpoint. */

import { useRef, useState } from 'react'
import { Avatar } from '@/shared/ui'
import { ApiError } from '@/shared/api'
import { uploadMyAvatar } from '@/entities/user'
import { useAuth } from '@/features/auth'

const MAX_BYTES = 5 * 1024 * 1024
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

export function AvatarUpload() {
  const { user, setUser } = useAuth()
  const inputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  if (!user) return null

  async function handleFile(file: File) {
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError('Поддерживаются JPEG, PNG и WebP')
      return
    }
    if (file.size > MAX_BYTES) {
      setError('Файл больше 5 МБ')
      return
    }
    setUploading(true)
    setError(null)
    try {
      setUser(await uploadMyAvatar(file))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не удалось загрузить аватар')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <div
        role="button"
        aria-label="Сменить аватар"
        title="Сменить аватар"
        style={{ cursor: 'pointer', opacity: uploading ? 0.5 : 1 }}
        onClick={() => inputRef.current?.click()}
      >
        <Avatar name={user.first_name} src={user.avatar_url} size="large" />
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED_TYPES.join(',')}
        style={{ display: 'none' }}
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) void handleFile(file)
          e.target.value = ''
        }}
      />
      {error && <p className="input-error-msg">{error}</p>}
    </div>
  )
}
