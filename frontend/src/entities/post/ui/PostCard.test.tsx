import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { Post } from '../model/types'
import { PostCard } from './PostCard'

const post: Post = {
  id: 1,
  title: 'Прекрасное утро!',
  content: 'Сегодня отличная погода',
  category: null,
  status: 'published',
  sentiment: 'positive',
  age_rating: '0+',
  likes_count: 12,
  comments_count: 3,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  author: {
    id: 2,
    login: 'alex',
    first_name: 'Алексей',
    last_name: 'Смирнов',
    avatar_url: null,
  },
}

function renderCard(extra: Partial<Parameters<typeof PostCard>[0]> = {}) {
  const onToggleLike = vi.fn()
  render(
    <MemoryRouter>
      <PostCard
        post={post}
        liked={false}
        likesCount={12}
        commentsCount={3}
        onToggleLike={onToggleLike}
        {...extra}
      />
    </MemoryRouter>,
  )
  return { onToggleLike }
}

describe('PostCard', () => {
  it('renders the author, title, text and badges', () => {
    renderCard()
    expect(screen.getByText('Алексей Смирнов')).toBeInTheDocument()
    expect(screen.getByText('Прекрасное утро!')).toBeInTheDocument()
    expect(screen.getByText('Сегодня отличная погода')).toBeInTheDocument()
    expect(screen.getByText('POSITIVE')).toBeInTheDocument()
    expect(screen.getByText('0+')).toBeInTheDocument()
  })

  it('clicking the heart calls onToggleLike with the current state', async () => {
    const { onToggleLike } = renderCard()
    await userEvent.click(screen.getByRole('button', { name: 'Лайк' }))
    expect(onToggleLike).toHaveBeenCalledWith(post, false)
  })

  it('shows the follow button only when a callback is provided', () => {
    renderCard()
    expect(screen.queryByText('+ Подписаться')).not.toBeInTheDocument()

    renderCard({ isFollowing: false, onToggleFollow: vi.fn() })
    expect(screen.getByText('+ Подписаться')).toBeInTheDocument()
  })

  it('renders comments lazily after the card is expanded', async () => {
    renderCard({ renderComments: () => <div data-testid="comments" /> })
    expect(screen.queryByTestId('comments')).not.toBeInTheDocument()
    await userEvent.click(screen.getByText('Прекрасное утро!'))
    expect(screen.getByTestId('comments')).toBeInTheDocument()
  })
})
