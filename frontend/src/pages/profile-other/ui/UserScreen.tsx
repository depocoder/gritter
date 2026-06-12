/* The API has no GET /users/{id}/profile, so the author info comes from
   their posts (GET /posts?author_id=X). With no posts only the id is known. */

import { useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Avatar, Button, Spinner } from '@/shared/ui'
import { fullName } from '@/shared/lib/format'
import { listPosts, PostCard, type Post } from '@/entities/post'
import { useAuth } from '@/features/auth'
import { useLikes } from '@/features/like'
import { useFollows } from '@/features/follow'
import { CommentsSection, useCommentCounts } from '@/features/comment'
import { usePaginatedList } from '@/pages/feed'

export function UserScreen() {
  const { userId } = useParams()
  // key remounts the view when navigating between user profiles
  return <UserView key={userId} authorId={Number(userId)} />
}

function UserView({ authorId }: { authorId: number }) {
  const { user: me } = useAuth()

  const fetchPage = useCallback(
    (page: number) => listPosts({ page, author_id: authorId }),
    [authorId],
  )
  const { items, loading, error, hasNext, total, loadMore } = usePaginatedList<Post>(fetchPage)
  const { isLiked, likesCountOf, toggleLike } = useLikes(me!.id)
  const { isFollowing, toggleFollow } = useFollows(me!.id)
  const { countOf, syncCount, bumpCount } = useCommentCounts()

  const renderComments = useCallback(
    (post: Post) => (
      <CommentsSection postId={post.id} onLoaded={syncCount} onCommentAdded={bumpCount} />
    ),
    [syncCount, bumpCount],
  )

  const author = items[0]?.author
  const following = isFollowing(authorId)

  return (
    <main className="feed-container">
      <section className="profile-header-custom">
        <Avatar
          name={author?.first_name ?? '?'}
          src={author?.avatar_url}
          size="large"
        />
        <div className="profile-info">
          <h2>{author ? fullName(author) : `Пользователь #${authorId}`}</h2>
          <div className="profile-stats">
            {author && <span>@{author.login}</span>}
            <span>{total} публикаций</span>
          </div>
          {me!.id !== authorId && (
            <div className="flex-row" style={{ marginTop: '1rem' }}>
              <Button
                variant="outline"
                size="small"
                onClick={() => toggleFollow(authorId, following)}
              >
                {following ? '✓ Отписаться' : '+ Подписаться'}
              </Button>
            </div>
          )}
        </div>
      </section>

      <h3 style={{ marginBottom: '1rem' }}>Посты</h3>
      {items.map((post) => (
        <PostCard
          key={post.id}
          post={post}
          liked={isLiked(post.id)}
          likesCount={likesCountOf(post)}
          commentsCount={countOf(post)}
          onToggleLike={toggleLike}
          renderComments={renderComments}
        />
      ))}
      {loading && <Spinner />}
      {error && <p className="state-message state-message--error">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="state-message">У пользователя пока нет опубликованных постов</p>
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
