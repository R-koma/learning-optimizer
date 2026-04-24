type AppEnv = "development" | "test" | "production";

interface RequiredUrls {
  apiUrl: string;
  wsUrl: string;
  authUrl: string;
}

function assertSecureUrl(name: string, value: string, env: AppEnv): void {
  if (env !== "production") return;
  const insecure = value.startsWith("http://") || value.startsWith("ws://");
  if (insecure) {
    throw new Error(
      `[env-guard] ${name} must use https:// or wss:// in production, got: ${value}`,
    );
  }
}

export function validateClientEnv(): RequiredUrls {
  const env = (process.env.NODE_ENV ?? "development") as AppEnv;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
  const authUrl =
    process.env.NEXT_PUBLIC_BETTER_AUTH_URL ?? "http://localhost:3000";

  assertSecureUrl("NEXT_PUBLIC_API_URL", apiUrl, env);
  assertSecureUrl("NEXT_PUBLIC_WS_URL", wsUrl, env);
  assertSecureUrl("NEXT_PUBLIC_BETTER_AUTH_URL", authUrl, env);

  return { apiUrl, wsUrl, authUrl };
}
