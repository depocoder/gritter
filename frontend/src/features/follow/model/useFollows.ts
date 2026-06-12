/* The API has no "am I following X" flag — per-user follow state lives in
   localStorage, reconciled with API replies (409 = already following,
   404 on DELETE = was not following). */

import { useCallback, useState } from 'react'
import { ApiError } from '@/shared/api'
import { followUser, unfollowUser } from '@/entities/user'

function readIds(storageKey: string): Set<number> {
  try {
    const raw = localStorage.getItem(storageKey)
    return raw ? new Set(JSON.parse(raw) as number[]) : new Set()
  } catch {
    return new Set()
  }
}

export interface FollowsApi {
  isFollowing: (userId: number) => boolean
  toggleFollow: (userId: number, currentlyFollowing: boolean) => void
}

export function useFollows(myUserId: number): FollowsApi {
  const storageKey = `gritter_following_${myUserId}`
  const [followingIds, setFollowingIds] = useState<Set<number>>(() => readIds(storageKey))

  const setFollowing = useCallback(
    (userId: number, following: boolean) => {
      setFollowingIds((prev) => {
        const next = new Set(prev)
        if (following) next.add(userId)
        else next.delete(userId)
        localStorage.setItem(storageKey, JSON.stringify([...next]))
        return next
      })
    },
    [storageKey],
  )

  const isFollowing = useCallback((userId: number) => followingIds.has(userId), [followingIds])

  const toggleFollow = useCallback(
    (userId: number, currentlyFollowing: boolean) => {
      setFollowing(userId, !currentlyFollowing) // optimistic
      const request = currentlyFollowing ? unfollowUser(userId) : followUser(userId)
      request.catch((error) => {
        if (error instanceof ApiError && error.status === 409) {
          setFollowing(userId, true) // was already following
        } else if (error instanceof ApiError && error.status === 404 && currentlyFollowing) {
          setFollowing(userId, false) // was not following
        } else {
          setFollowing(userId, currentlyFollowing) // roll back
        }
      })
    },
    [setFollowing],
  )

  return { isFollowing, toggleFollow }
}
