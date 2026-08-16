import type { Metadata } from "next";

type PublicMetadataFallback = {
  readonly title: string;
  readonly description: string;
};

type PublicMetadataPayload = {
  readonly title?: unknown;
  readonly summary?: unknown;
};

const backendOrigin = (
  process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

function nonBlankString(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const normalized = value.trim();
  return normalized || undefined;
}

export async function getPublicCmsMetadata(
  contentKey: string,
  fallback: PublicMetadataFallback,
): Promise<Metadata> {
  try {
    const response = await fetch(
      `${backendOrigin}/api/v1/content/${encodeURIComponent(contentKey)}`,
      {
        headers: { accept: "application/json" },
        next: { revalidate: 60 },
      },
    );
    if (!response.ok) return fallback;

    const payload = (await response.json()) as PublicMetadataPayload;
    return {
      title: nonBlankString(payload.title) ?? fallback.title,
      description: nonBlankString(payload.summary) ?? fallback.description,
    };
  } catch {
    return fallback;
  }
}
