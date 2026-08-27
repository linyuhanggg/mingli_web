export const BAZI_PREVIEW_READING_QUERY = "reading";

type SearchLike = {
  get(name: string): string | null;
  toString(): string;
};

export function readBaziPreviewReadingId(searchParams: SearchLike): string | null {
  const value = searchParams.get(BAZI_PREVIEW_READING_QUERY)?.trim() ?? "";
  return value ? value : null;
}

export function baziPreviewHref(
  pathname: string,
  searchParams: SearchLike,
  readingId: string | null,
  profileVersionId?: string | null,
): string {
  const next = new URLSearchParams(searchParams.toString());
  if (readingId) {
    next.set(BAZI_PREVIEW_READING_QUERY, readingId);
  } else {
    next.delete(BAZI_PREVIEW_READING_QUERY);
  }
  const profile = profileVersionId?.trim();
  if (profile) {
    next.set("profile", profile);
  }
  const query = next.toString();
  return query ? `${pathname}?${query}` : pathname;
}
