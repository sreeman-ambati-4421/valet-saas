export type UserRole = 'platform_super_admin' | 'tenant_admin' | 'venue_manager' | 'valet'

export type SessionState =
  | 'REQUESTED'
  | 'ASSIGNED'
  | 'VEHICLE_COLLECTED'
  | 'PARKED'
  | 'RETRIEVAL_REQUESTED'
  | 'RETRIEVING'
  | 'READY'
  | 'DELIVERED'
  | 'COMPLETED'
  | 'CANCELLED'

export interface VenueSummary {
  id: string
  name: string
}

export interface Tenant {
  id: string
  name: string
  is_active: boolean
  created_at: string
}

export interface Venue {
  id: string
  tenant_id: string
  name: string
  address: string | null
  timezone: string
  is_active: boolean
  created_at: string
}

export interface Me {
  id: string
  email: string
  full_name: string
  role: UserRole
  tenant_id: string | null
  venues: VenueSummary[]
}

export interface ValetSession {
  id: string
  tenant_id: string
  venue_id: string
  guest_id: string
  vehicle_id: string
  assigned_valet_id: string | null
  state: SessionState
  parking_zone_id: string | null
  parking_slot_id: string | null
  key_tag: string | null
  created_at: string
  updated_at: string
  registration_number: string | null
  guest_phone_number: string | null
}

export interface SessionEvent {
  id: string
  actor_user_id: string | null
  from_state: string | null
  to_state: string
  note: string | null
  created_at: string
}

export interface SessionDetail extends ValetSession {
  events: SessionEvent[]
}
