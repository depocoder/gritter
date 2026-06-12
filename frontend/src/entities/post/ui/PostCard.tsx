import { memo, useCallback, useState } from 'react'
import type { MouseEvent, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, Button } from '@/shared/ui'
import { formatRelativeDate, fullName } from '@/shared/lib/format'
import type { Post } from '../model/types'

interface PostCardProps {
  post: Post
  likesCount: number
  commentsCount: number
  liked: boolean
  onToggleLike: (post: Post, liked: boolean) => void
  /** undefined hides the follow button (own posts) */
  isFollowing?: boolean
  onToggleFollow?: (authorId: number, following: boolean) => void
  statusBadge?: string
  /** Rendered only when the card is expanded, so comments load lazily */
  renderComments?: (post: Post) => ReactNode
}

/* memo: props are primitives and page-stable callbacks, so liking one post
   does not re-render its siblings. */
export const PostCard = memo(function PostCard({
  post,
  likesCount,
  commentsCount,
  liked,
  onToggleLike,
  isFollowing,
  onToggleFollow,
  statusBadge,
  renderComments,
}: PostCardProps) {
  const [expanded, setExpanded] = useState(false)

  const handleCardClick = useCallback(() => {
    if (renderComments) setExpanded((prev) => !prev)
  }, [renderComments])

  const handleLike = useCallback(
    (event: MouseEvent) => {
      event.stopPropagation()
      onToggleLike(post, liked)
    },
    [onToggleLike, post, liked],
  )

  const handleFollow = useCallback(
    (event: MouseEvent) => {
      event.stopPropagation()
      onToggleFollow?.(post.author.id, isFollowing ?? false)
    },
    [onToggleFollow, post.author.id, isFollowing],
  )

  return (
    <article className="post-card" onClick={handleCardClick}>
      <div className="post-card__header">
        <Avatar name={post.author.first_name} src={post.author.avatar_url} />
        <div className="post-card__author">
          <div className="post-card__name">
            <Link
              to={`/users/${post.author.id}`}
              style={{ color: 'inherit', fontSize: 'inherit' }}
              onClick={(event) => event.stopPropagation()}
            >
              {fullName(post.author)}
            </Link>
          </div>
          <div className="post-card__date">{formatRelativeDate(post.created_at)}</div>
        </div>
        {onToggleFollow && (
          <Button variant="outline" size="small" onClick={handleFollow}>
            {isFollowing ? '✓ Отписаться' : '+ Подписаться'}
          </Button>
        )}
      </div>

      <div className="post-card__content">
        <div className="post-card__title">{post.title}</div>
        <div className="post-card__text">{post.content}</div>
      </div>

      {(post.sentiment || post.age_rating || post.category || statusBadge) && (
        <div className="post-card__meta">
          {statusBadge && <span className="meta-badge meta-badge--moderation">{statusBadge}</span>}
          {post.sentiment && (
            <span
              className={`meta-badge ${
                post.sentiment === 'negative' ? 'meta-badge--negative' : 'meta-badge--positive'
              }`}
            >
              {post.sentiment.toUpperCase()}
            </span>
          )}
          {post.age_rating && <span className="meta-badge meta-badge--age">{post.age_rating}</span>}
          {post.category && <span className="meta-badge">#{post.category}</span>}
        </div>
      )}

      <div className="post-card__stats">
        <span onClick={handleLike} role="button" aria-label={liked ? 'Убрать лайк' : 'Лайк'}>
          <span className={`material-icons ${liked ? 'liked' : ''}`}>
            {liked ? 'favorite' : 'favorite_border'}
          </span>{' '}
          {likesCount}
        </span>
        <span role="button" aria-label="Комментарии">
          <span className="material-icons">chat_bubble_outline</span> {commentsCount}
        </span>
      </div>

      {expanded && renderComments && (
        <div onClick={(event) => event.stopPropagation()}>{renderComments(post)}</div>
      )}
    </article>
  )
})
