import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/features/auth'
import { Spinner } from '@/shared/ui'

export function ProtectedRoute() {
  const { user, initializing } = useAuth()
  if (initializing) return <Spinner />
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}
