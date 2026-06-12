/* post.comments_count is a denormalized snapshot and can drift; once the
   comments section loads, the badge re-syncs with the real total. */

import { useCallback, useState } from 'react'
import type { Post } from '@/entities/post'

export interface CommentCountsApi {
  countOf: (post: Post) => number
  syncCount: (postId: number, total: number) => void
  bumpCount: (postId: number) => void
}

export function useCommentCounts(): CommentCountsApi {
  const [counts, setCounts] = useState<ReadonlyMap<number, number>>(new Map())

  const syncCount = useCallback((postId: number, total: number) => {
    setCounts((prev) => new Map(prev).set(postId, total))
  }, [])

  const bumpCount = useCallback((postId: number) => {
    setCounts((prev) => new Map(prev).set(postId, (prev.get(postId) ?? 0) + 1))
  }, [])

  const countOf = useCallback(
    (post: Post) => counts.get(post.id) ?? post.comments_count,
    [counts],
  )

  return { countOf, syncCount, bumpCount }
}
