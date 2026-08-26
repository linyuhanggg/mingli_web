export type PublicKeyLabel = {
  readonly key: string;
  readonly label: string;
};

const INTERNAL_KEY = /^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$/;

export function isInternalKey(value: string): boolean {
  return INTERNAL_KEY.test(value);
}

export function labelForPublicKey(
  labels: readonly PublicKeyLabel[] | undefined,
  key: string,
): string | undefined {
  return labels?.find((item) => item.key === key)?.label;
}

export function displayPublicText(
  labels: readonly PublicKeyLabel[] | undefined,
  value: string,
  fallbacks: Readonly<Record<string, string>> = {},
): string {
  return (
    labelForPublicKey(labels, value) ??
    fallbacks[value] ??
    (isInternalKey(value) ? "" : value)
  );
}
