/* Pages are lazy so each screen ships as its own chunk. */

import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '@/features/auth'
import { Spinner } from '@/shared/ui'
import { AppLayout } from './AppLayout'
import { ProtectedRoute } from './ProtectedRoute'
import './styles/global.css'

const LoginScreen = lazy(() =>
  import('@/pages/login').then((m) => ({ default: m.LoginScreen })),
)
const FeedScreen = lazy(() => import('@/pages/feed').then((m) => ({ default: m.FeedScreen })))
const ProfileScreen = lazy(() =>
  import('@/pages/profile').then((m) => ({ default: m.ProfileScreen })),
)
const UserScreen = lazy(() =>
  import('@/pages/profile-other').then((m) => ({ default: m.UserScreen })),
)

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<Spinner />}>
          <Routes>
            <Route path="/login" element={<LoginScreen />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/feed" element={<FeedScreen />} />
                <Route path="/profile" element={<ProfileScreen />} />
                <Route path="/users/:userId" element={<UserScreen />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/feed" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  )
}
