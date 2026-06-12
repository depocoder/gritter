import { apiFetch } from '@/shared/api'
import type { FollowOut, User } from '../model/types'

export function getMyProfile(): Promise<User> {
  return apiFetch<User>('/users/me/profile')
}

export function uploadMyAvatar(file: File): Promise<User> {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch<User>('/users/me/avatar', { method: 'POST', formData })
}

export function followUser(userId: number): Promise<FollowOut> {
  return apiFetch<FollowOut>(`/users/${userId}/follow`, { method: 'POST' })
}

export function unfollowUser(userId: number): Promise<void> {
  return apiFetch<void>(`/users/${userId}/follow`, { method: 'DELETE' })
}
