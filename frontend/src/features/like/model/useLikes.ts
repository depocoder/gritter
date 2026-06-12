/* Optimistic likes. The API is idempotent but PostOut has no "liked by me"
   flag, so per-user liked state lives in localStorage (see README). */

import { useCallback, useState } from 'react'
import { likePost, unlikePost, type Post } from '@/entities/post'

function readLikedIds(storageKey: string): Set<number> {
  try {
    const raw = localStorage.getItem(storageKey)
    return raw ? new Set(JSON.parse(raw) as number[]) : new Set()
  } catch {
    return new Set()
  }
}

export interface LikesApi {
  isLiked: (postId: number) => boolean
  /** Optimistic override, falling back to the server value */
  likesCountOf: (post: Post) => number
  toggleLike: (post: Post, currentlyLiked: boolean) => void
}

export function useLikes(userId: number): LikesApi {
  const storageKey = `gritter_liked_${userId}`
  const [likedIds, setLikedIds] = useState<Set<number>>(() => readLikedIds(storageKey))
  const [countOverrides, setCountOverrides] = useState<ReadonlyMap<number, number>>(new Map())

  const persist = useCallback(
    (ids: Set<number>) => {
      localStorage.setItem(storageKey, JSON.stringify([...ids]))
    },
    [storageKey],
  )

  const setLiked = useCallback(
    (postId: number, liked: boolean) => {
      setLikedIds((prev) => {
        const next = new Set(prev)
        if (liked) next.add(postId)
        else next.delete(postId)
        persist(next)
        return next
      })
    },
    [persist],
  )

  const setCount = useCallback((postId: number, count: number) => {
    setCountOverrides((prev) => new Map(prev).set(postId, count))
  }, [])

  const isLiked = useCallback((postId: number) => likedIds.has(postId), [likedIds])

  const likesCountOf = useCallback(
    (post: Post) => countOverrides.get(post.id) ?? post.likes_count,
    [countOverrides],
  )

  const toggleLike = useCallback(
    (post: Post, currentlyLiked: boolean) => {
      const countBefore = countOverrides.get(post.id) ?? post.likes_count
      const optimisticCount = currentlyLiked ? Math.max(0, countBefore - 1) : countBefore + 1
      setLiked(post.id, !currentlyLiked)
      setCount(post.id, optimisticCount)

      const request = currentlyLiked
        ? unlikePost(post.id)
        : likePost(post.id).then((state) => setCount(post.id, state.likes_count))

      request.catch(() => {
        // roll back the optimistic update
        setLiked(post.id, currentlyLiked)
        setCount(post.id, countBefore)
      })
    },
    [countOverrides, setLiked, setCount],
  )

  return { isLiked, likesCountOf, toggleLike }
}
