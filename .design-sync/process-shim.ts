// Design-sync only, imported first from ds-entry.ts. next/link's bundled
// client code probes process.env.__NEXT_* feature flags at module
// top-level; the browser preview environment has no `process` global at
// all, so any bare `process.env.*` access throws before window.MingliWeb
// is ever assigned — crashing every component in the bundle, not just the
// one that imports next/link. This makes the identifier exist.
if (typeof (globalThis as { process?: unknown }).process === "undefined") {
  (globalThis as { process?: unknown }).process = { env: {} };
}
export {};
