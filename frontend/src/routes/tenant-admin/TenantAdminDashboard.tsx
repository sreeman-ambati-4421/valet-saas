import { Layout } from '../../components/Layout'

export function TenantAdminDashboard() {
  return (
    <Layout title="Tenant Admin">
      <p className="text-gray-400">
        Venue, user, and QR code management is coming in Phase 4 (Management Dashboards). For now, venues and
        staff can be provisioned via the API directly.
      </p>
    </Layout>
  )
}
