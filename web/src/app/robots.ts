import type { MetadataRoute } from "next";


export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
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
    },
  };
}
