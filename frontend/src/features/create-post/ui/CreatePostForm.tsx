/* New posts go to moderation: on success we show moderation_message,
   the post appears in the feed only once published. */

import { useState, type FormEvent } from 'react'
import { Avatar, Button, Input } from '@/shared/ui'
import { ApiError } from '@/shared/api'
import { createPost } from '@/entities/post'
import { useAuth } from '@/features/auth'

export function CreatePostForm() {
  const { user } = useAuth()
  const [expanded, setExpanded] = useState(false)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (!user) return null

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!title.trim() || !content.trim()) {
      setError('Заполните заголовок и текст поста')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const created = await createPost({ title: title.trim(), content: content.trim() })
      setNotice(created.moderation_message)
      setTitle('')
      setContent('')
      setExpanded(false)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не удалось создать пост')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="create-post-row" onSubmit={handleSubmit}>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
        <Avatar name={user.first_name} src={user.avatar_url} size="small" />
        <Input
          placeholder="Что нового? (заголовок)"
          value={title}
          onFocus={() => setExpanded(true)}
          onChange={(e) => setTitle(e.target.value)}
        />
        {!expanded && (
          <Button size="small" onClick={() => setExpanded(true)}>
            Поделиться
          </Button>
        )}
      </div>
      {expanded && (
        <>
          <Input
            placeholder="Расскажите подробнее…"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <div className="flex-row" style={{ justifyContent: 'flex-end', gap: '0.5rem' }}>
            <Button
              variant="outline"
              size="small"
              onClick={() => {
                setExpanded(false)
                setError(null)
              }}
            >
              Отмена
            </Button>
            <Button type="submit" size="small" disabled={submitting}>
              {submitting ? 'Отправляем…' : 'Поделиться'}
            </Button>
          </div>
        </>
      )}
      {error && <p className="input-error-msg">{error}</p>}
      {notice && <p className="state-message">{notice}</p>}
    </form>
  )
}
