export type AdminIdentityKind = "users" | "subjects" | "user-detail" | "subject-detail";

export type AdminUserSummary = {
  id: string;
  status: string;
  created_at: string;
  identity_count: number;
  consent_count: number;
  subject_count: number;
  active_session_count: number;
};

export type AdminUsersResponse = { users: readonly AdminUserSummary[] };

export type AdminUserIdentity = {
  id: string;
  provider: string;
  masked_destination: string;
  destination: string | null;
  status: string;
  verified_at: string;
  created_at: string;
};

export type AdminUserConsent = {
  id: string;
  policy_key: string;
  policy_version: string;
  context: string;
  accepted_at: string;
};

export type AdminUserSession = {
  id: string;
  status: "active" | "expired" | "revoked";
  expires_at: string;
  last_seen_at: string;
  revoked_at: string | null;
  created_at: string;
};

export type AdminUserSubjectSummary = {
  id: string;
  label: string | null;
  status: string;
  created_at: string;
  version_count: number;
  latest_version: number | null;
};

export type AdminUserResponse = {
  id: string;
  status: string;
  created_at: string;
  identities: readonly AdminUserIdentity[];
  consents: readonly AdminUserConsent[];
  sessions: readonly AdminUserSession[];
  subjects: readonly AdminUserSubjectSummary[];
};

export type AdminSubjectSummary = {
  id: string;
  owner_user_id: string | null;
  label: string | null;
  status: string;
  created_at: string;
  version_count: number;
  latest_version: number | null;
};

export type AdminSubjectsResponse = { subjects: readonly AdminSubjectSummary[] };

export type AdminSubjectAuthorization = {
  subject_type: string;
  is_minor: boolean;
  authorization_confirmed: boolean;
  photo_authorization_confirmed: boolean;
  minor_guardian_confirmed: boolean;
  difference_acknowledged: boolean;
};

export type AdminSubjectProfile = {
  birth_datetime: string;
  timezone: string;
  location: string;
  gender: "male" | "female" | "other";
  time_basis_policy: "civil" | "solar" | "lunar";
  zi_hour_policy: "midnight" | "substitute" | "solar";
  longitude: number | null;
  latitude: number | null;
  coordinate_source: string | null;
};

export type AdminSubjectVersion = {
  id: string;
  version: number;
  created_at: string;
  authorization: AdminSubjectAuthorization | null;
  profile: AdminSubjectProfile;
};

export type AdminSubjectResponse = {
  id: string;
  owner_user_id: string | null;
  label: string | null;
  status: string;
  created_at: string;
  versions: readonly AdminSubjectVersion[];
};
