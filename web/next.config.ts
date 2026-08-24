import path from "node:path";
import type { NextConfig } from "next";

const backendOrigin = (
  process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");
const developmentEval = process.env.NODE_ENV === "production" ? "" : " 'unsafe-eval'";

const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "form-action 'self'",
  `script-src 'self' 'unsafe-inline'${developmentEval}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "media-src 'self'",
  "worker-src 'self' blob:",
].join("; ");

const privateHeaders = [
  { key: "Cache-Control", value: "private, no-store, max-age=0" },
  { key: "X-Robots-Tag", value: "noindex, nofollow, noarchive" },
];

const privateRouteSources = [
  "/app/:path*",
  "/account/:path*",
  "/auth/:path*",
  "/workbench/:path*",
  "/checkout/:path*",
  "/share/:path*",
  "/invite/:path*",
] as const;

const legacyRedirects = [
  { source: "/app", destination: "/account", permanent: false },
  { source: "/app/profiles", destination: "/account/profiles", permanent: false },
  { source: "/app/profile/new", destination: "/account/profiles", permanent: false },
  { source: "/app/readings", destination: "/account/history", permanent: false },
  {
    source: "/app/readings/:readingId",
    destination: "/account/history/:readingId",
    permanent: false,
  },
  { source: "/app/bazi", destination: "/bazi", permanent: false },
  { source: "/app/ask/liuyao", destination: "/liuyao", permanent: false },
  { source: "/canwen", destination: "/hecan", permanent: true },
  { source: "/time-check", destination: "/tools/time-check", permanent: false },
  { source: "/zeri", destination: "/selection", permanent: false },
] as const;

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  outputFileTracingRoot: path.join(__dirname, ".."),
  poweredByHeader: false,
  reactStrictMode: true,
  turbopack: {
    root: path.join(__dirname, ".."),
  },
  async redirects() {
    return [...legacyRedirects];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: contentSecurityPolicy },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), payment=()",
          },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
        ],
      },
      ...privateRouteSources.map((source) => ({ source, headers: privateHeaders })),
      {
        source: "/api/:path*",
        headers: [{ key: "Cache-Control", value: "private, no-store, max-age=0" }],
      },
    ];
  },
};

export default nextConfig;
