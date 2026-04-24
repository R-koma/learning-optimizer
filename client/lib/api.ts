const API_BASE_URL =
  (typeof window === "undefined" && process.env.API_URL_INTERNAL) ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";
const AUTH_BASE_URL =
  process.env.NEXT_PUBLIC_BETTER_AUTH_URL || "http://localhost:3000";

interface CachedToken {
  token: string;
  expiresAt: number;
}

const tokenCache = new Map<string, CachedToken>();
const SKEW_MS = 60_000;

export async function getToken(cookieHeader?: string): Promise<string> {
  if (cookieHeader) {
    const cached = tokenCache.get(cookieHeader);
    if (cached && cached.expiresAt - SKEW_MS > Date.now()) {
      return cached.token;
    }
  }

  const res = await fetch(`${AUTH_BASE_URL}/api/auth/token`, {
    headers: cookieHeader ? { Cookie: cookieHeader } : undefined,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Token fetch failed: ${res.status}`);
  const { token } = (await res.json()) as { token: string };

  if (cookieHeader) {
    const parts = token.split(".");
    if (parts.length >= 3) {
      const payload = JSON.parse(
        Buffer.from(parts[1], "base64url").toString("utf8"),
      ) as { exp: number };
      tokenCache.set(cookieHeader, { token, expiresAt: payload.exp * 1000 });
    }
  }

  return token;
}

export async function fetchAPI<T>(
  path: string,
  options?: RequestInit & { token?: string },
): Promise<T> {
  const authToken = options?.token ?? (await getToken());

  const { token: _, ...restOptions } = options ?? {};
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...restOptions,
    headers: {
      Authorization: `Bearer ${authToken}`,
      "Content-Type": "application/json",
      ...restOptions?.headers,
    },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
