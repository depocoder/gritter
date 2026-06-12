import { apiFetch } from '@/shared/api'
import type { FeedItem, MyPost, Paginated, Post, PostCreated } from '../model/types'

export interface ListPostsParams {
  page?: number
  size?: number
  author_id?: number
}

export function listPosts(params: ListPostsParams = {}): Promise<Paginated<Post>> {
  const query = new URLSearchParams()
  if (params.page) query.set('page', String(params.page))
  if (params.size) query.set('size', String(params.size))
  if (params.author_id) query.set('author_id', String(params.author_id))
  const qs = query.toString()
  return apiFetch<Paginated<Post>>(`/posts${qs ? `?${qs}` : ''}`)
}

export function listMyPosts(page = 1): Promise<Paginated<MyPost>> {
  return apiFetch<Paginated<MyPost>>(`/posts/me?page=${page}`)
}

export function getMyFeed(page = 1): Promise<Paginated<FeedItem>> {
  return apiFetch<Paginated<FeedItem>>(`/users/me/feed?page=${page}`)
}

export function createPost(data: {
  title: string
  content: string
  category?: string
}): Promise<PostCreated> {
  return apiFetch<PostCreated>('/posts', { method: 'POST', body: data })
}

export function likePost(postId: number): Promise<{ liked: boolean; likes_count: number }> {
  return apiFetch(`/posts/${postId}/like`, { method: 'POST' })
}

export function unlikePost(postId: number): Promise<void> {
  return apiFetch<void>(`/posts/${postId}/like`, { method: 'DELETE' })
}
