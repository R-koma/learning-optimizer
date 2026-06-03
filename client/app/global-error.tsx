"use client";

import { useEffect } from "react";

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

// global-error はルートレイアウト自体を置換するため、自前の <html>/<body> を
// 描画する必要がある。globals.css も適用されないため、依存のないインラインスタイルで構成する。
export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="ja">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, sans-serif",
          backgroundColor: "#0a0a0a",
          color: "#ededed",
        }}
      >
        <div
          style={{ maxWidth: "28rem", padding: "2rem", textAlign: "center" }}
        >
          <h1 style={{ fontSize: "1.25rem", marginBottom: "0.75rem" }}>
            問題が発生しました
          </h1>
          <p
            style={{
              fontSize: "0.875rem",
              opacity: 0.8,
              marginBottom: "1.5rem",
            }}
          >
            予期しないエラーが発生しました。時間をおいて再試行してください。
          </p>
          <button
            onClick={() => reset()}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "0.875rem",
              borderRadius: "0.5rem",
              border: "none",
              cursor: "pointer",
              backgroundColor: "#ededed",
              color: "#0a0a0a",
            }}
          >
            再試行
          </button>
        </div>
      </body>
    </html>
  );
}
