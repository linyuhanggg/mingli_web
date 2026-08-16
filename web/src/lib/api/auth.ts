import type { AuthSessionResponse } from "./contracts";
import { jsonPost } from "./client";

export type PasswordLoginPayload = {
  channel: "phone" | "email";
  destination: string;
  password: string;
};

export type OtpChallengeResponse = {
  challenge_id: string;
  expires_at?: string;
  retry_after_seconds?: number;
  development_code?: string;
};

export type PasswordRecoveryPayload = {
  challenge_id: string;
  code: string;
  password: string;
};

export type RegistrationPayload = {
  challenge_id: string;
  code: string;
  password: string;
  policy_version: string;
};

export type ConsentPayload = {
  policy_key: "privacy" | "terms";
  policy_version: string;
  context: "registration" | "purchase" | "reaccept";
};

export async function loginWithPassword(
  payload: PasswordLoginPayload,
): Promise<AuthSessionResponse> {
  return jsonPost<AuthSessionResponse>("/api/v1/auth/password/login", payload);
}

export async function requestOtp(
  payload: Pick<PasswordLoginPayload, "channel" | "destination">,
): Promise<OtpChallengeResponse> {
  return jsonPost<OtpChallengeResponse>("/api/v1/auth/otp/request", payload);
}

export async function recoverPassword(
  payload: PasswordRecoveryPayload,
): Promise<AuthSessionResponse> {
  return jsonPost<AuthSessionResponse>("/api/v1/auth/password/recover", payload);
}

export async function registerWithOtp(
  payload: RegistrationPayload,
): Promise<AuthSessionResponse> {
  return jsonPost<AuthSessionResponse>("/api/v1/auth/register", payload);
}

export async function setPassword(password: string): Promise<void> {
  await jsonPost<void>("/api/v1/auth/password", { password });
}

export async function recordConsent(payload: ConsentPayload): Promise<unknown> {
  return jsonPost<unknown>("/api/v1/auth/consents", payload);
}
