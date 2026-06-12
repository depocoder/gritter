/* Mirrors the backend pydantic schemas (auth/schema.py, profile/schema.py). */

export interface User {
  id: number
  first_name: string
  last_name: string
  login: string
  avatar_url: string | null
  created_at: string
}

export interface FollowOut {
  follower_id: number
  followee_id: number
  created_at: string
}
