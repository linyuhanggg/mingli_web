import nextConfig from "../../next.config";
import manifest from "@/app/manifest";
import robots from "@/app/robots";


function headerMap(headers: Array<{ key: string; value: string }>) {
  return Object.fromEntries(headers.map(({ key, value }) => [key, value]));
}

describe("same-origin and private-surface configuration", () => {
  it("allows local browser hosts to load development client resources", () => {
    expect(nextConfig.allowedDevOrigins).toEqual(["127.0.0.1", "localhost"]);
  });

  it("proxies browser API requests to the internal FastAPI service", async () => {
    expect(nextConfig.rewrites).toBeTypeOf("function");
    const rewrites = await nextConfig.rewrites!();

    expect(rewrites).toContainEqual({
      source: "/api/:path*",
      destination: "http://127.0.0.1:8000/api/:path*",
    });
  });

  it("adds baseline browser security headers", async () => {
    expect(nextConfig.headers).toBeTypeOf("function");
    const rules = await nextConfig.headers!();
    const globalRule = rules.find((rule) => rule.source === "/:path*");
    const headers = headerMap(globalRule?.headers ?? []);

    expect(headers["X-Content-Type-Options"]).toBe("nosniff");
    expect(headers["Referrer-Policy"]).toBe("strict-origin-when-cross-origin");
    expect(headers["X-Frame-Options"]).toBe("DENY");
    expect(headers["Permissions-Policy"]).toContain("camera=()");
    expect(headers["Content-Security-Policy"]).toContain("default-src 'self'");
    expect(headers["Content-Security-Policy"]).toContain("frame-ancestors 'none'");
    expect(headers["Content-Security-Policy"]).toContain("'unsafe-eval'");
  });

  it.each([
    "/app/:path*",
    "/account/:path*",
    "/auth/:path*",
    "/workbench/:path*",
    "/checkout/:path*",
    "/share/:path*",
    "/invite/:path*",
  ])(
    "prevents caching and indexing for %s",
    async (source) => {
      const rules = await nextConfig.headers!();
      const privateRule = rules.find((rule) => rule.source === source);
      const headers = headerMap(privateRule?.headers ?? []);

      expect(headers["Cache-Control"]).toBe("private, no-store, max-age=0");
      expect(headers["X-Robots-Tag"]).toBe("noindex, nofollow, noarchive");
    },
  );

  it("keeps private surfaces out of robots and exposes only a public PWA manifest", () => {
    const robotsConfig = robots();
    const manifestConfig = manifest();

    expect(robotsConfig.rules).toEqual({
      userAgent: "*",
      allow: "/",
      disallow: [
        "/app/",
        "/account",
        "/auth/",
        "/workbench/",
        "/checkout/",
        "/share/",
        "/invite/",
        "/api/",
      ],
    });
    expect(manifestConfig).toMatchObject({
      name: "命理工具",
      short_name: "命理工具",
      start_url: "/",
      display: "standalone",
    });
  });
});
