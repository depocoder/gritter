import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Post } from '@/entities/post'
import { useLikes } from './useLikes'

const { likePostMock, unlikePostMock } = vi.hoisted(() => ({
  likePostMock: vi.fn(),
  unlikePostMock: vi.fn(),
}))

vi.mock('@/entities/post', () => ({
  likePost: likePostMock,
  unlikePost: unlikePostMock,
}))

const post = { id: 7, likes_count: 10 } as Post

describe('useLikes', () => {
  it('likes optimistically and re-syncs the count with the server reply', async () => {
    likePostMock.mockResolvedValue({ liked: true, likes_count: 11 })
    const { result } = renderHook(() => useLikes(1))

    act(() => result.current.toggleLike(post, false))

    // immediately, before the server responds
    expect(result.current.isLiked(7)).toBe(true)
    expect(result.current.likesCountOf(post)).toBe(11)

    await waitFor(() => expect(likePostMock).toHaveBeenCalledWith(7))
    expect(result.current.likesCountOf(post)).toBe(11)
  })

  it('rolls back when the request fails', async () => {
    likePostMock.mockRejectedValue(new Error('network down'))
    const { result } = renderHook(() => useLikes(1))

    act(() => result.current.toggleLike(post, false))
    expect(result.current.isLiked(7)).toBe(true)

    await waitFor(() => expect(result.current.isLiked(7)).toBe(false))
    expect(result.current.likesCountOf(post)).toBe(10)
  })

  it('unlikes and decrements the count', async () => {
    unlikePostMock.mockResolvedValue(undefined)
    localStorage.setItem('gritter_liked_1', JSON.stringify([7]))
    const { result } = renderHook(() => useLikes(1))

    expect(result.current.isLiked(7)).toBe(true)
    act(() => result.current.toggleLike(post, true))

    expect(result.current.isLiked(7)).toBe(false)
    expect(result.current.likesCountOf(post)).toBe(9)
    await waitFor(() => expect(unlikePostMock).toHaveBeenCalledWith(7))
  })

  it('persists liked ids per user in localStorage', () => {
    localStorage.setItem('gritter_liked_42', JSON.stringify([1, 2]))
    const { result } = renderHook(() => useLikes(42))
    expect(result.current.isLiked(1)).toBe(true)
    expect(result.current.isLiked(3)).toBe(false)
  })
})
