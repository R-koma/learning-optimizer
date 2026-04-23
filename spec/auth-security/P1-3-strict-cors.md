# P1-3: CORS の厳格化

**優先度**: P1
**対象ブランチ**: `security/strict-cors`

---

## 背景

- `server/main.py:34-35` で `allow_methods=["*"]`, `allow_headers=["*"]`
- `allow_credentials=True` との組み合わせは仕様上ブラウザ拒否されうるが、明示列挙が望ましい
- 実際に Cookie を FastAPI に送っていないので `allow_credentials` は不要

## 実装内容

`server/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)
```

## 受け入れ基準

- [ ] `curl -H "Origin: https://evil.example" -H "Access-Control-Request-Method: POST" -X OPTIONS http://api/...` が `Access-Control-Allow-Origin` を返さない
- [ ] 許可 Origin からの Preflight が `Authorization` ヘッダ許可を返す
- [ ] 既存フロントからの全 API 呼び出しが成功する（E2E で確認）

## テスト方法

```python
def test_cors_rejects_unknown_origin(client):
    r = client.options(
        "/api/notes",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in r.headers
```
