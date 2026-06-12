import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Spinner } from '@/shared/ui'
import { formatRelativeDate } from '@/shared/lib/format'
import {
  getMyFeed,
  listPosts,
  PostCard,
  type FeedItem,
  type Post,
} from '@/entities/post'
import { useAuth } from '@/features/auth'
import { useLikes } from '@/features/like'
import { useFollows } from '@/features/follow'
import { CommentsSection, useCommentCounts } from '@/features/comment'
import { CreatePostForm } from '@/features/create-post'
import { usePaginatedList } from '../model/usePaginatedList'

type FeedTab = 'all' | 'following'

export function FeedScreen() {
  const { user } = useAuth()
  const [tab, setTab] = useState<FeedTab>('all')
  return (
    <main className="feed-container">
      <CreatePostForm />
      <div className="feed-tabs" role="tablist">
        <button
          role="tab"
          aria-selected={tab === 'all'}
          className={`auth-tab ${tab === 'all' ? 'active' : ''}`}
          onClick={() => setTab('all')}
        >
          Все посты
        </button>
        <button
          role="tab"
          aria-selected={tab === 'following'}
          className={`auth-tab ${tab === 'following' ? 'active' : ''}`}
          onClick={() => setTab('following')}
        >
          Подписки
        </button>
      </div>
      {tab === 'all' ? <AllPostsFeed myUserId={user!.id} /> : <FollowingFeed />}
    </main>
  )
}

function AllPostsFeed({ myUserId }: { myUserId: number }) {
  const fetchPage = useCallback((page: number) => listPosts({ page }), [])
  const { items, loading, error, hasNext, loadMore } = usePaginatedList<Post>(fetchPage)

  const { isLiked, likesCountOf, toggleLike } = useLikes(myUserId)
  const { isFollowing, toggleFollow } = useFollows(myUserId)
  const { countOf, syncCount, bumpCount } = useCommentCounts()

  const renderComments = useCallback(
    (post: Post) => (
      <CommentsSection postId={post.id} onLoaded={syncCount} onCommentAdded={bumpCount} />
    ),
    [syncCount, bumpCount],
  )

  return (
    <>
      {items.map((post) => (
        <PostCard
          key={post.id}
          post={post}
          liked={isLiked(post.id)}
          likesCount={likesCountOf(post)}
          commentsCount={countOf(post)}
          onToggleLike={toggleLike}
          isFollowing={post.author.id === myUserId ? undefined : isFollowing(post.author.id)}
          onToggleFollow={post.author.id === myUserId ? undefined : toggleFollow}
          renderComments={renderComments}
        />
      ))}
      {loading && <Spinner />}
      {error && <p className="state-message state-message--error">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="state-message">Постов пока нет — создайте первый!</p>
      )}
      {hasNext && !loading && (
        <div className="load-more-row">
          <Button variant="outline" onClick={loadMore}>
            Показать ещё
          </Button>
        </div>
      )}
    </>
  )
}

function FollowingFeed() {
  const fetchPage = useCallback((page: number) => getMyFeed(page), [])
  const { items, loading, error, hasNext, loadMore } = usePaginatedList<FeedItem>(fetchPage)
  const navigate = useNavigate()

  /* The following feed has no author or counters (see README), so the card
     is reduced and clicking it opens the author's profile instead. */
  const cards = useMemo(
    () =>
      items.map((item) => (
        <article
          key={item.id}
          className="post-card"
          title="Открыть профиль автора"
          onClick={() => navigate(`/users/${item.user_id}`)}
        >
          <div className="post-card__content" style={{ paddingTop: '1rem' }}>
            <div className="post-card__title">{item.title}</div>
            <div className="post-card__text">{item.content}</div>
            <div className="post-card__date" style={{ marginTop: '0.5rem' }}>
              {formatRelativeDate(item.created_at)}
            </div>
          </div>
        </article>
      )),
    [items, navigate],
  )

  return (
    <>
      {cards}
      {loading && <Spinner />}
      {error && <p className="state-message state-message--error">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="state-message">
          В ленте подписок пусто — подпишитесь на кого-нибудь во вкладке «Все посты»
        </p>
      )}
      {hasNext && !loading && (
        <div className="load-more-row">
          <Button variant="outline" onClick={loadMore}>
            Показать ещё
          </Button>
        </div>
      )}
    </>
  )
}
