const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const AUTH_BASE_URL =
  process.env.NEXT_PUBLIC_BETTER_AUTH_URL || "http://localhost:3000";

export async function getToken(cookieHeader?: string): Promise<string> {
  const res = await fetch(`${AUTH_BASE_URL}/api/auth/token`, {
    headers: cookieHeader ? { Cookie: cookieHeader } : undefined,
  });
  if (!res.ok) throw new Error(`Token fetch failed: ${res.status}`);
  const { token } = await res.json();
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
