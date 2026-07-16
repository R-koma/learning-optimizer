import type { MetadataRoute } from "next";

const baseUrl =
  process.env.NEXT_PUBLIC_BETTER_AUTH_URL || "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/learn", "/notes", "/review", "/api"],
    },
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
