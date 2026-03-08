import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import BottomNav from './components/BottomNav'
import ChatPage from './pages/ChatPage'
import DiscoverPage from './pages/DiscoverPage'
import SettingsPage from './pages/SettingsPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ProfilePage from './pages/ProfilePage'
import ChatWindow from './components/ChatWindow'
import AdminPage from './pages/AdminPage'
import { useAuth } from './context/AuthContext'

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" />
}

function PublicRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <Navigate to="/discover" /> : children
}

function App() {
  function AdminRoute({ children }) {
    const { isAuthenticated, user } = useAuth()
    if (!isAuthenticated) return <Navigate to="/login" />
    const isAdmin = user?.role === 'admin' || user?.username === 'superadmin'
    return isAdmin ? children : <Navigate to="/discover" />
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-neutral-100 dark:bg-neutral-900">
        <Routes>
          {/* 登录和注册页面 - 公共路由 */}
          <Route path="/login" element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          } />
          <Route path="/register" element={
            <PublicRoute>
              <RegisterPage />
            </PublicRoute>
          } />

          {/* 主应用页面 - 需要登录 */}
          <Route path="/" element={
            <ProtectedRoute>
              <Navigate to="/discover" replace />
            </ProtectedRoute>
          } />

          <Route path="/chat" element={
            <ProtectedRoute>
              <ChatPage />
            </ProtectedRoute>
          } />

          <Route path="/chat/:userId" element={
            <ProtectedRoute>
              <ChatWindow />
            </ProtectedRoute>
          } />

          <Route path="/discover" element={
            <ProtectedRoute>
              <DiscoverPage />
            </ProtectedRoute>
          } />

          <Route path="/settings" element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          } />

          <Route path="/profile" element={
            <ProtectedRoute>
              <ProfilePage />
            </ProtectedRoute>
          } />

          <Route path="/admin" element={
            <AdminRoute>
              <AdminPage />
            </AdminRoute>
          } />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
