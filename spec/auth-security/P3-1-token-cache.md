# P3-1: トークン取得のキャッシュ

**優先度**: P3
**対象ブランチ**: `perf/token-cache`

---

## 背景

- Server Component が毎リクエストで `GET /api/auth/token` を呼ぶ（`client/lib/api.ts:8`, `client/app/(main)/notes/page.tsx:18`）
- 15 分有効の JWT を毎回発行するのは無駄

## 実装内容

`client/lib/api.ts`:

```typescript
interface CachedToken {
  token: string;
  expiresAt: number;
}

const tokenCache = new Map<string, CachedToken>();
const SKEW_MS = 60_000;

export async function getToken(cookieHeader?: string): Promise<string> {
  const key = cookieHeader ?? "__client__";
  const cached = tokenCache.get(key);
  if (cached && cached.expiresAt - SKEW_MS > Date.now()) {
    return cached.token;
  }

  const res = await fetch(`${AUTH_BASE_URL}/api/auth/token`, {
    headers: cookieHeader ? { Cookie: cookieHeader } : undefined,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Token fetch failed: ${res.status}`);
  const { token } = await res.json();

  const payload = JSON.parse(
    Buffer.from(token.split(".")[1], "base64url").toString("utf8"),
  ) as { exp: number };

  tokenCache.set(key, { token, expiresAt: payload.exp * 1000 });
  return token;
}
```

## 受け入れ基準

- [ ] 連続する同じ `cookieHeader` での `getToken()` 呼び出しで `/api/auth/token` への HTTP リクエストは 1 回のみ
- [ ] 有効期限 1 分前で再フェッチが発生する

## テスト方法

```typescript
test("getToken caches within exp window", async () => {
  const spy = vi.spyOn(global, "fetch").mockResolvedValue(/* ... */);
  await getToken("cookie=abc");
  await getToken("cookie=abc");
  expect(spy).toHaveBeenCalledTimes(1);
});
```

## 注意事項（セキュリティ）

- Server Component のリクエスト間で `tokenCache` が共有されるのはセキュリティ境界的に問題あり
- ユーザ A の Cookie が来たときキー一致なら他人の JWT が返る可能性
- **キーに必ず Cookie ヘッダ全文（またはそのハッシュ）を使う** こと
- `"__client__"` 固定は**単一プロセスのシングルユーザ**前提で、マルチテナントの Server では危険
- Node.js / Edge 実行モデル次第なので、実装前に Next.js のプロセスモデルを再確認すること
