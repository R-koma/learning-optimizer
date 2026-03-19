"use client";

import { useState, useRef, useCallback } from "react";

type MessageRole = "user" | "assistant";

interface ChatMessage {
  role: MessageRole;
  content: string;
}

interface ServerMessage {
  type:
    | "assistant_message"
    | "note_generated"
    | "feedback_generated"
    | "session_ended"
    | "error";
  content?: string;
  detail?: string;
  note_id?: string;
  topic?: string;
  summary?: string;
}

interface UseChatWebSocketReturn {
  messages: ChatMessage[];
  isConnected: boolean;
  isLoading: boolean;
  isSessionEnded: boolean;
  generatedNote: { note_id: string; topic: string; summary: string } | null;
  error: string | null;
  startLearning: (topic: string) => void;
  sendMessage: (content: string) => void;
  endSession: () => void;
}

export function useChatWebSocket(): UseChatWebSocketReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSessionEnded, setIsSessionEnded] = useState(false);
  const [generatedNote, setGeneratedNote] = useState<{
    note_id: string;
    topic: string;
    summary: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(async () => {
    const res = await fetch("/api/auth/token");
    const { token } = await res.json();
    if (!token) {
      setError("認証トークンの取得に失敗しました");
      return;
    }

    const ws = new WebSocket("ws://localhost:8000/ws/chat");

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "authenticate", token }));
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      const data: ServerMessage = JSON.parse(event.data);

      switch (data.type) {
        case "assistant_message":
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: data.content ?? "" },
          ]);
          setIsLoading(false);
          break;

        case "note_generated":
          setGeneratedNote({
            note_id: data.note_id ?? "",
            topic: data.topic ?? "",
            summary: data.summary ?? "",
          });
          break;

        case "session_ended":
          setIsSessionEnded(true);
          setIsLoading(false);
          break;

        case "error":
          setError(data.detail ?? "Unknown error");
          setIsLoading(false);
          break;
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onerror = () => {
      setError("WebSocket connection failed");
      setIsConnected(false);
    };

    wsRef.current = ws;
  }, []);

  const startLearning = useCallback(
    (topic: string) => {
      connect();

      const checkAndSend = () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "start_learning", topic }));
          setMessages([{ role: "user", content: topic }]);
          setIsLoading(true);
          setIsSessionEnded(false);
          setGeneratedNote(null);
        } else {
          setTimeout(checkAndSend, 50);
        }
      };
      checkAndSend();
    },
    [connect],
  );

  const sendMessage = useCallback((content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({ type: "user_message", content }));
    setMessages((prev) => [...prev, { role: "user", content }]);
    setIsLoading(true);
  }, []);

  const endSession = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({ type: "end_session" }));
  }, []);

  return {
    messages,
    isConnected,
    isLoading,
    isSessionEnded,
    generatedNote,
    error,
    startLearning,
    sendMessage,
    endSession,
  };
}
