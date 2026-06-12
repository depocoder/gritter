import { apiFetch } from '@/shared/api'
import type { Comment, PaginatedComments } from '../model/types'

export function listComments(postId: number, page = 1): Promise<PaginatedComments> {
  return apiFetch<PaginatedComments>(`/posts/${postId}/comments?page=${page}`)
}

export function createComment(postId: number, content: string): Promise<Comment> {
  return apiFetch<Comment>(`/posts/${postId}/comments`, {
    method: 'POST',
    body: { content },
  })
}
