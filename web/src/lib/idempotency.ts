import { createIdempotencyKey } from "./api";

export type IntentKey = {
  fingerprint: string;
  key: string;
};

export function stableKeyForIntent(
  current: IntentKey | null,
  intent: unknown,
): IntentKey {
  const fingerprint = JSON.stringify(intent);
  if (current?.fingerprint === fingerprint) {
    return current;
  }
  return { fingerprint, key: createIdempotencyKey() };
}
