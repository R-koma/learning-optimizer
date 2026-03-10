"use client";

import { useState } from "react";

type NotesResponse = {
  detail?: string;
  notes?: unknown[];
  user_id?: string;
};

export default function TestNotes() {
  const [response, setResponse] = useState<NotesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchNotes = async () => {
    setError(null);

    try {
      const resToken = await fetch("/api/auth/token");
      if (!resToken.ok) {
        const message = `JWTエンドポイントへのアクセスに失敗しました。ステータス: ${resToken.status}`;
        console.error(message);
        setError(message);
        return;
      }

      const tokenData = (await resToken.json()) as { token?: string };
      const token = tokenData.token;

      if (!token) {
        const message =
          "トークンが空です。BetterAuthの設定を見直す必要があるかもしれません。";
        console.error(message, tokenData);
        setError(message);
        return;
      }

      const res = await fetch("http://localhost:8000/api/notes", {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      const result = await res.json().catch(() => null);

      if (!res.ok) {
        const detail =
          typeof result?.detail === "string"
            ? result.detail
            : `ステータス: ${res.status}`;
        const message = `FastAPI側でエラーが発生しました。${detail}`;
        console.error(message, result);
        setError(message);
        setResponse(result);
        return;
      }

      setResponse(result);
    } catch (err) {
      console.error("通信エラー:", err);
      setError(
        "通信エラーが発生しました。FastAPI または Next.js が起動中か確認してください。",
      );
    }
  };

  return (
    <div className="p-4">
      <button
        onClick={fetchNotes}
        className="bg-blue-500 text-white px-4 py-2 rounded"
      >
        FastAPIからノートを取得
      </button>
      {error ? (
        <p className="mt-4 rounded bg-red-100 p-3 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <pre className="mt-4 p-4 bg-gray-100 rounded">
        {JSON.stringify(response, null, 2)}
      </pre>
    </div>
  );
}
