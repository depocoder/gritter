import { useCallback, useState, type FormEvent } from 'react'
import { Button, Input, Spinner } from '@/shared/ui'
import { ApiError } from '@/shared/api'
import { fullName } from '@/shared/lib/format'
import { listMyPosts, PostCard, type MyPost } from '@/entities/post'
import { changePasswordRequest, useAuth, PASSWORD_MIN } from '@/features/auth'
import { useLikes } from '@/features/like'
import { CommentsSection, useCommentCounts } from '@/features/comment'
import { AvatarUpload } from '@/features/upload-avatar'
import { usePaginatedList } from '@/pages/feed'

export function ProfileScreen() {
  const { user } = useAuth()
  const fetchPage = useCallback((page: number) => listMyPosts(page), [])
  const { items, loading, error, hasNext, total, loadMore } =
    usePaginatedList<MyPost>(fetchPage)
  const { isLiked, likesCountOf, toggleLike } = useLikes(user!.id)
  const { countOf, syncCount, bumpCount } = useCommentCounts()
  const [showPasswordForm, setShowPasswordForm] = useState(false)

  const renderComments = useCallback(
    (post: { id: number }) => (
      <CommentsSection postId={post.id} onLoaded={syncCount} onCommentAdded={bumpCount} />
    ),
    [syncCount, bumpCount],
  )

  if (!user) return null

  return (
    <main className="feed-container">
      <section className="profile-header-custom">
        <AvatarUpload />
        <div className="profile-info">
          <h2>{fullName(user)}</h2>
          <div className="profile-stats">
            <span>@{user.login}</span>
            <span>{total} публикаций</span>
          </div>
          <div className="flex-row" style={{ marginTop: '1rem', gap: '0.75rem' }}>
            <Button
              variant="outline"
              size="small"
              onClick={() => setShowPasswordForm((v) => !v)}
            >
              Сменить пароль
            </Button>
          </div>
          {showPasswordForm && (
            <ChangePasswordForm onDone={() => setShowPasswordForm(false)} />
          )}
        </div>
      </section>

      <h3 style={{ marginBottom: '1rem' }}>Мои посты</h3>
      {items.map((post) => (
        <PostCard
          key={post.id}
          post={post}
          liked={isLiked(post.id)}
          likesCount={likesCountOf(post)}
          commentsCount={countOf(post)}
          onToggleLike={toggleLike}
          statusBadge={post.is_on_moderation ? 'НА МОДЕРАЦИИ' : undefined}
          renderComments={post.is_on_moderation ? undefined : renderComments}
        />
      ))}
      {loading && <Spinner />}
      {error && <p className="state-message state-message--error">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="state-message">У вас пока нет постов</p>
      )}
      {hasNext && !loading && (
        <div className="load-more-row">
          <Button variant="outline" onClick={loadMore}>
            Показать ещё
          </Button>
        </div>
      )}
    </main>
  )
}

function ChangePasswordForm({ onDone }: { onDone: () => void }) {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (newPassword.length < PASSWORD_MIN) {
      setError(`Новый пароль — минимум ${PASSWORD_MIN} символов`)
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await changePasswordRequest(oldPassword, newPassword)
      setNotice('Пароль изменён')
      setTimeout(onDone, 1200)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не удалось сменить пароль')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ marginTop: '1rem', maxWidth: 320 }}>
      <div className="form-group">
        <Input
          label="Текущий пароль"
          type="password"
          value={oldPassword}
          onChange={(e) => setOldPassword(e.target.value)}
        />
      </div>
      <div className="form-group">
        <Input
          label="Новый пароль"
          type="password"
          value={newPassword}
          error={error ?? undefined}
          onChange={(e) => setNewPassword(e.target.value)}
        />
      </div>
      {notice && <p className="state-message">{notice}</p>}
      <Button type="submit" size="small" disabled={submitting}>
        Сохранить
      </Button>
    </form>
  )
}
