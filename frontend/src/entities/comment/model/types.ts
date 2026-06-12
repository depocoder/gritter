/* Mirrors the backend pydantic schemas (comments/schema.py). */
import type { Author, Paginated } from '@/entities/post'

export interface Comment {
  id: number
  post_id: number
  content: string
  created_at: string
  author: Author
}

export type PaginatedComments = Paginated<Comment>
