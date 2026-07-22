export type UserRole = 'saas_owner' | 'business_owner' | 'valet_desk'

export type SessionState =
  | 'REQUESTED'
  | 'ACCEPTED'
  | 'PARKED'
  | 'RETRIEVAL_REQUESTED'
  | 'RETRIEVING'
  | 'READY'
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

export type TagStatus = 'available' | 'in_use'

export interface QRCode {
  id: string
  venue_id: string
  token: string
  label: string | null
  is_active: boolean
  status: TagStatus
  wa_link: string
}

export interface Me {
  id: string
  phone_number: string
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
  vehicle_id: string | null
  qr_code_id: string | null
  accepted_by_user_id: string | null
  created_via_whatsapp: boolean
  state: SessionState
  parking_zone_id: string | null
  parking_slot_id: string | null
  created_at: string
  updated_at: string
  registration_number: string | null
  guest_phone_number: string | null
  tag_label: string | null
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
