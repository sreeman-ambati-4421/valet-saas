import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { RoleHome } from './auth/RoleHome'
import { LoginPage } from './auth/LoginPage'
import { AcceptInvite } from './auth/AcceptInvite'
import { PrivacyPolicy } from './legal/PrivacyPolicy'
import { ValetDeskDashboard } from './routes/valet-desk/ValetDeskDashboard'
import { BusinessOwnerDashboard } from './routes/business-owner/BusinessOwnerDashboard'
import { SaasOwnerDashboard } from './routes/saas-owner/SaasOwnerDashboard'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/accept-invite" element={<AcceptInvite />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/" element={<RoleHome />} />
          <Route
            path="/valet-desk"
            element={
              <ProtectedRoute allowedRoles={['valet_desk']}>
                <ValetDeskDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/business-owner"
            element={
              <ProtectedRoute allowedRoles={['business_owner']}>
                <BusinessOwnerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/saas-owner"
            element={
              <ProtectedRoute allowedRoles={['saas_owner']}>
                <SaasOwnerDashboard />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
