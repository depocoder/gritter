import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Post } from '@/entities/post'
import { useCommentCounts } from './useCommentCounts'

const post = { id: 5, comments_count: 3 } as Post

describe('useCommentCounts', () => {
  it('shows the server snapshot before the section loads', () => {
    const { result } = renderHook(() => useCommentCounts())
    expect(result.current.countOf(post)).toBe(3)
  })

  it('re-syncs the badge with the API total after loading', () => {
    const { result } = renderHook(() => useCommentCounts())
    act(() => result.current.syncCount(5, 1)) // the DB actually has 1 comment
    expect(result.current.countOf(post)).toBe(1)
  })

  it('increments the synced value when a comment is added', () => {
    const { result } = renderHook(() => useCommentCounts())
    act(() => result.current.syncCount(5, 1))
    act(() => result.current.bumpCount(5))
    expect(result.current.countOf(post)).toBe(2)
  })

  it('keeps counters of different posts independent', () => {
    const { result } = renderHook(() => useCommentCounts())
    act(() => result.current.syncCount(5, 10))
    expect(result.current.countOf({ id: 6, comments_count: 7 } as Post)).toBe(7)
  })
})
