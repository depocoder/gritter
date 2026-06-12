/* Mirrors the backend pydantic schemas (posts/schema.py, profile/schema.py). */

export interface Author {
  id: number
  login: string
  first_name: string
  last_name: string
  avatar_url: string | null
}

export type PostStatus = 'draft' | 'on_moderation' | 'published' | 'rejected'

export interface Post {
  id: number
  title: string
  content: string
  category: string | null
  status: PostStatus
  sentiment: string | null
  age_rating: string | null
  likes_count: number
  comments_count: number
  created_at: string
  updated_at: string
  author: Author
}

export interface MyPost extends Post {
  is_on_moderation: boolean
}

export interface PostCreated {
  id: number
  status: PostStatus
  moderation_message: string
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  size: number
  has_next: boolean
}

/** Item of `/users/me/feed` — no author or counters in the backend schema. */
export interface FeedItem {
  id: number
  user_id: number
  title: string
  content: string
  category: string | null
  created_at: string
}
