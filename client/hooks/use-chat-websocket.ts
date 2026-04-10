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
    | "cancel_last_message_success"
    | "cancel_last_message_error"
    | "error";
  content?: string;
  detail?: string;
  note_id?: string;
  topic?: string;
  summary?: string;
  understanding_level?: string;
  strength?: string;
  improvements?: string;
  cancelled_content?: string;
}

interface Feedback {
  understanding_level: string;
  strength: string;
  improvements: string;
}

interface UseChatWebSocketReturn {
  messages: ChatMessage[];
  isConnected: boolean;
  isLoading: boolean;
  isSessionEnded: boolean;
  isGeneratingNote: boolean;
  generatedNote: { note_id: string; topic: string; summary: string } | null;
  feedback: Feedback | null;
  error: string | null;
  editingMessage: string | null;
  startLearning: (topic: string) => void;
  startReview: (noteId: string) => void;
  sendMessage: (content: string) => void;
  endSession: () => void;
  cancelLastMessage: () => void;
  clearEditingMessage: () => void;
}

export function useChatWebSocket(): UseChatWebSocketReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSessionEnded, setIsSessionEnded] = useState(false);
  const [isGeneratingNote, setIsGeneratingNote] = useState(false);
  const [generatedNote, setGeneratedNote] = useState<{
    note_id: string;
    topic: string;
    summary: string;
  } | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingMessage, setEditingMessage] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(async () => {
    const res = await fetch("/api/auth/token");
    const { token } = await res.json();
    if (!token) {
      setError("認証トークンの取得に失敗しました");
      return;
    }

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
    const ws = new WebSocket(`${wsUrl}/ws/chat`);

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
          setIsGeneratingNote(false);
          break;

        case "feedback_generated":
          setFeedback({
            understanding_level: data.understanding_level ?? "",
            strength: data.strength ?? "",
            improvements: data.improvements ?? "",
          });
          break;

        case "session_ended":
          setIsSessionEnded(true);
          setIsLoading(false);
          setIsGeneratingNote(false);
          break;

        case "cancel_last_message_success":
          setMessages((prev) => prev.slice(0, -2));
          setEditingMessage(data.cancelled_content ?? "");
          break;

        case "cancel_last_message_error":
          setError(data.detail ?? "Cancel failed");
          break;

        case "error":
          setError(data.detail ?? "Unknown error");
          setIsLoading(false);
          setIsGeneratingNote(false);
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
          setFeedback(null);
        } else {
          setTimeout(checkAndSend, 50);
        }
      };
      checkAndSend();
    },
    [connect],
  );

  const startReview = useCallback(
    (noteId: string) => {
      connect();

      const checkAndSend = () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({ type: "start_review", note_id: noteId }),
          );
          setMessages([]);
          setIsLoading(true);
          setIsSessionEnded(false);
          setGeneratedNote(null);
          setFeedback(null);
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
    setIsLoading(true);
    setIsGeneratingNote(true);
  }, []);

  const cancelLastMessage = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({ type: "cancel_last_message" }));
  }, []);

  const clearEditingMessage = useCallback(() => {
    setEditingMessage(null);
  }, []);

  return {
    messages,
    isConnected,
    isLoading,
    isSessionEnded,
    isGeneratingNote,
    generatedNote,
    feedback,
    error,
    editingMessage,
    startLearning,
    startReview,
    sendMessage,
    endSession,
    cancelLastMessage,
    clearEditingMessage,
  };
}
