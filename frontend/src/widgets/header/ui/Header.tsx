/* Lives in the layout, so it survives navigation. The mockup's search box
   is intentionally absent: search is P3 in the user stories. */

import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Avatar } from '@/shared/ui'
import { useAuth } from '@/features/auth'

export function Header() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  // Clicking "Лента" while already on the feed scrolls to the top
  const handleFeedClick = () => {
    setMenuOpen(false)
    if (pathname === '/feed') window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <nav className="navbar">
      <div className="navbar__container">
        <Link to="/feed" className="navbar__logo" onClick={handleFeedClick}>
          Gritter
        </Link>
        <ul className={`navbar__menu ${menuOpen ? 'active' : ''}`}>
          <li>
            <Link to="/feed" className="navbar__link" onClick={handleFeedClick}>
              Лента
            </Link>
          </li>
          <li>
            <button
              className="navbar__link"
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              Выйти
            </button>
          </li>
          {user && (
            <li>
              <Link to="/profile" onClick={() => setMenuOpen(false)} aria-label="Мой профиль">
                <Avatar name={user.first_name} src={user.avatar_url} size="small" />
              </Link>
            </li>
          )}
        </ul>
        <button
          className="navbar__toggle"
          aria-label="Меню"
          onClick={() => setMenuOpen((open) => !open)}
        >
          ☰
        </button>
      </div>
    </nav>
  )
}
