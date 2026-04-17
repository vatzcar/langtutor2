export interface Language {
  id: string;
  name: string;
  locale: string;
  is_default: boolean;
  is_fallback: boolean;
  is_active: boolean;
  icon_url?: string | null;
  created_at?: string;
  updated_at?: string;
}

export type PersonaGender = 'male' | 'female' | 'nonbinary' | string;
export type PersonaType = 'teacher' | 'coordinator' | 'peer';
export type TeachingStyle = 'casual_friendly' | 'friendly_structured' | 'formal_structured';

export interface Persona {
  id: string;
  name: string;
  language_id: string;
  gender: PersonaGender;
  type: PersonaType;
  teaching_style: TeachingStyle;
  is_active: boolean;
  image_url?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface Plan {
  id: string;
  slug: 'free' | 'pro' | 'ultra' | string;
  name: string;
  price_monthly: number;
  price_yearly: number;
  // Limit values:
  //   -1 = Not Available
  //    0 = Unlimited
  //   >0 = specific number of minutes
  text_learning_limit_minutes: number;        // per day
  voice_call_limit_minutes: number;           // per day
  video_call_limit_minutes: number;           // per day
  agentic_voice_limit_monthly: number;        // per month
  coordinator_video_limit_monthly: number;    // per month
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  native_language_id: string | null;
  is_active: boolean;
  is_banned: boolean;
  ban_reason?: string | null;
  ban_expires_at?: string | null;
  created_at: string;
}

export interface AdminRole {
  id: string;
  name: string;
  permissions: string[];
  created_at?: string;
}

export interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  role_id: string | null;
  role?: AdminRole | null;
  is_active: boolean;
  created_at: string;
}

export interface Subscription {
  id: string;
  user_id: string;
  plan_id: string;
  plan?: Plan | null;
  started_at: string;
  expires_at: string | null;
  is_active: boolean;
}

export interface AuditLog {
  id: string;
  actor_type: string;
  actor_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  created_at: string;
  metadata?: Record<string, unknown> | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email?: string;
}

export interface AdminMe {
  id: string;
  email: string;
  name: string;
  role: { id: string; name: string; permissions: string[] };
}

// Re-export for backwards compatibility.
export { ALL_PERMISSIONS as PERMISSIONS } from '../constants/permissions';
export type { Permission } from '../constants/permissions';
