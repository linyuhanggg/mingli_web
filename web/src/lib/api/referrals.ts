import type {
  ReferralAttributionCaptureResponse,
  ReferralPublicResponse,
} from "./contracts";
import { jsonDelete, jsonPost, requestJson } from "./client";

export async function getReferralInvite(code: string): Promise<ReferralPublicResponse> {
  return requestJson<ReferralPublicResponse>(
    `/api/v1/referrals/${encodeURIComponent(code)}`,
  );
}

export async function recordReferralAttribution(
  code: string,
): Promise<ReferralAttributionCaptureResponse> {
  return jsonPost<ReferralAttributionCaptureResponse>(
    `/api/v1/referrals/${encodeURIComponent(code)}/attribution`,
    {},
  );
}

export async function clearReferralAttribution(code: string): Promise<void> {
  await jsonDelete<void>(
    `/api/v1/referrals/${encodeURIComponent(code)}/attribution`,
  );
}
