/* Persistent shell: the Header survives navigation, only Outlet changes. */

import { Outlet } from 'react-router-dom'
import { Header } from '@/widgets/header'

export function AppLayout() {
  return (
    <>
      <Header />
      <Outlet />
      <footer className="page-footer">© 2026 Gritter. Все права защищены.</footer>
    </>
  )
}
