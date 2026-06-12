/* Mounted only when the post card is expanded, so comments load lazily. */

import { useEffect, useState, type FormEvent } from 'react'
import { Button, Input, Spinner } from '@/shared/ui'
import { ApiError } from '@/shared/api'
import { createComment, listComments, CommentItem, type Comment } from '@/entities/comment'

interface CommentsSectionProps {
  postId: number
  onCommentAdded?: (postId: number) => void
  /** Reports the real total so the page can re-sync the card badge */
  onLoaded?: (postId: number, total: number) => void
}

export function CommentsSection({ postId, onCommentAdded, onLoaded }: CommentsSectionProps) {
  const [comments, setComments] = useState<Comment[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    listComments(postId)
      .then((page) => {
        if (cancelled) return
        setComments(page.items)
        onLoaded?.(postId, page.total)
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof ApiError ? err.message : 'Не удалось загрузить комментарии')
      })
    return () => {
      cancelled = true
    }
  }, [postId, onLoaded])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const content = text.trim()
    if (!content) return
    setSubmitting(true)
    setError(null)
    try {
      const comment = await createComment(postId, content)
      setComments((prev) => [...(prev ?? []), comment])
      setText('')
      onCommentAdded?.(postId)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не удалось отправить комментарий')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="comments-section">
      {comments === null && !error && <Spinner />}
      {error && <p className="state-message state-message--error">{error}</p>}
      {comments?.length === 0 && (
        <p className="state-message">Комментариев пока нет — будьте первым!</p>
      )}
      {comments?.map((comment) => <CommentItem key={comment.id} comment={comment} />)}
      <form className="comment-input-wrapper" onSubmit={handleSubmit}>
        <Input
          placeholder="Написать комментарий..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <Button type="submit" size="small" disabled={submitting || !text.trim()}>
          Отправить
        </Button>
      </form>
    </div>
  )
}
