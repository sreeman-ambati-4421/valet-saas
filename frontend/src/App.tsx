import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { RoleHome } from './auth/RoleHome'
import { LoginPage } from './auth/LoginPage'
import { ValetDashboard } from './routes/valet/ValetDashboard'
import { ManagerDashboard } from './routes/manager/ManagerDashboard'
import { TenantAdminDashboard } from './routes/tenant-admin/TenantAdminDashboard'
import { PlatformAdminDashboard } from './routes/platform-admin/PlatformAdminDashboard'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<RoleHome />} />
          <Route
            path="/valet"
            element={
              <ProtectedRoute allowedRoles={['valet']}>
                <ValetDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/manager"
            element={
              <ProtectedRoute allowedRoles={['venue_manager', 'tenant_admin']}>
                <ManagerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tenant-admin"
            element={
              <ProtectedRoute allowedRoles={['tenant_admin']}>
                <TenantAdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/platform-admin"
            element={
              <ProtectedRoute allowedRoles={['platform_super_admin']}>
                <PlatformAdminDashboard />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
