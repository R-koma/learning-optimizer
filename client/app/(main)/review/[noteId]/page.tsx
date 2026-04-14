"use client";

import { useRef, useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useChatWebSocket } from "@/hooks/use-chat-websocket";
import { useNavbarSlot } from "@/context/navbar-slot-context";
import { fetchAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ChatInput } from "@/components/chat/chat-input";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeftIcon,
  LogOutIcon,
  NotebookPenIcon,
  RotateCcwIcon,
  SparklesIcon,
  CheckCircleIcon,
  TrendingUpIcon,
  AlertCircleIcon,
  PencilIcon,
} from "lucide-react";

interface Note {
  id: string;
  topic: string;
  content: string;
  summary: string;
}

const LEVEL_CONFIG = {
  high: {
    label: "高い",
    variant: "default" as const,
    className: "bg-green-600",
  },
  medium: { label: "普通", variant: "secondary" as const, className: "" },
  low: { label: "低い", variant: "destructive" as const, className: "" },
};

export default function ReviewPage({
  params,
}: {
  params: Promise<{ noteId: string }>;
}) {
  const router = useRouter();
  const { noteId } = use(params);
  const [note, setNote] = useState<Note | null>(null);
  const [input, setInput] = useState("");
  const [isReviewStarted, setIsReviewStarted] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { setNavbarCenter } = useNavbarSlot();

  const {
    messages,
    isLoading,
    isSessionEnded,
    feedback,
    error,
    editingMessage,
    startReview,
    sendMessage,
    endSession,
    cancelLastMessage,
    clearEditingMessage,
  } = useChatWebSocket();

  useEffect(() => {
    fetchAPI<Note>(`/api/notes/${noteId}`)
      .then(setNote)
      .catch((e) => setLoadError(e.message));
  }, [noteId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  if (editingMessage !== null) {
    setInput(editingMessage);
    clearEditingMessage();
  }

  useEffect(() => {
    if (isReviewStarted && note) {
      setNavbarCenter(
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <RotateCcwIcon className="h-4 w-4 text-primary shrink-0" />
            <h1 className="text-sm font-semibold">{note.topic}</h1>
            <Badge variant="secondary" className="text-xs">
              復習
            </Badge>
          </div>
          <div className="h-4 w-px bg-border" />
          <div className="flex items-center gap-1">
            <div className="group relative">
              <Button
                variant="ghost"
                size="icon"
                onClick={endSession}
                className="h-8 w-8 rounded-full cursor-pointer"
              >
                <NotebookPenIcon className="h-4.5 w-4.5" />
              </Button>
              <span className="pointer-events-none absolute top-full left-1/2 mt-1 -translate-x-1/2 whitespace-nowrap rounded-md border bg-popover px-2 py-1 text-xs opacity-0 shadow-sm transition-opacity group-hover:opacity-100">
                ノート作成
              </span>
            </div>
            <div className="group relative">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => router.push("/dashboard")}
                className="h-8 w-8 rounded-full cursor-pointer"
              >
                <LogOutIcon className="h-4.5 w-4.5" />
              </Button>
              <span className="pointer-events-none absolute top-full left-1/2 mt-1 -translate-x-1/2 whitespace-nowrap rounded-md border bg-popover px-2 py-1 text-xs opacity-0 shadow-sm transition-opacity group-hover:opacity-100">
                会話を終了
              </span>
            </div>
          </div>
        </div>,
      );
    } else {
      setNavbarCenter(null);
    }
    return () => setNavbarCenter(null);
  }, [isReviewStarted, note, endSession, router, setNavbarCenter]);

  const handleStartReview = () => {
    if (!note) return;
    setIsReviewStarted(true);
    startReview(noteId);
  };

  const handleSendMessage = (content: string) => {
    if (!content.trim()) return;
    sendMessage(content);
    setInput("");
  };

  if (loadError) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-destructive">{loadError}</p>
      </div>
    );
  }

  if (!note) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">読み込み中...</p>
      </div>
    );
  }

  if (!isReviewStarted) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-8">
        <Link
          href={`/notes/${noteId}`}
          className="mb-6 inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          ノートに戻る
        </Link>

        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <RotateCcwIcon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">復習</h1>
            <p className="text-sm text-muted-foreground">{note.topic}</p>
          </div>
        </div>

        <div className="mb-8 rounded-xl border bg-card p-6">
          <div className="mb-3 flex items-center gap-2">
            <SparklesIcon className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-primary">
              前回の要約
            </h2>
          </div>
          <ul className="space-y-2 pl-1">
            {note.summary.split("\n").map((line, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-base leading-relaxed"
              >
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/60" />
                {line}
              </li>
            ))}
          </ul>
        </div>

        <Button
          onClick={handleStartReview}
          size="lg"
          className="w-full gap-2 cursor-pointer"
        >
          <RotateCcwIcon className="h-5 w-5" />
          復習を開始する
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {error && (
        <div className="px-6 py-2 text-sm text-destructive">{error}</div>
      )}

      <div className="flex-1 overflow-y-auto px-6">
        <div className="mx-auto max-w-3xl space-y-4 py-6">
          {messages.map((msg, i) => {
            const isLastUserMessage =
              msg.role === "user" &&
              i === messages.length - 2 &&
              messages.length >= 4 &&
              messages[messages.length - 1].role === "assistant" &&
              !isLoading &&
              !isSessionEnded;

            return (
              <div
                key={i}
                className={`group flex items-start gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-3 text-base leading-relaxed whitespace-pre-wrap ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  {msg.content}
                </div>
                {isLastUserMessage && (
                  <button
                    type="button"
                    onClick={cancelLastMessage}
                    className="mt-2 cursor-pointer opacity-0 transition-opacity group-hover:opacity-100"
                    title="編集して再送信"
                  >
                    <PencilIcon className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                  </button>
                )}
              </div>
            );
          })}

          {feedback && (
            <div className="mx-auto max-w-md space-y-4 rounded-xl border bg-card p-6">
              <div className="text-center">
                <CheckCircleIcon className="mx-auto mb-3 h-8 w-8 text-primary" />
                <h2 className="mb-1 font-semibold">復習が完了しました</h2>
                <p className="text-xs text-muted-foreground">
                  復習スケジュールが更新されました
                </p>
              </div>

              <div className="flex items-center justify-center gap-2">
                <span className="text-sm text-muted-foreground">理解度:</span>
                <Badge
                  className={
                    LEVEL_CONFIG[
                      feedback.understanding_level as keyof typeof LEVEL_CONFIG
                    ]?.className
                  }
                  variant={
                    LEVEL_CONFIG[
                      feedback.understanding_level as keyof typeof LEVEL_CONFIG
                    ]?.variant ?? "secondary"
                  }
                >
                  {LEVEL_CONFIG[
                    feedback.understanding_level as keyof typeof LEVEL_CONFIG
                  ]?.label ?? feedback.understanding_level}
                </Badge>
              </div>

              {feedback.strength && (
                <div>
                  <div className="mb-1 flex items-center gap-1 text-xs font-semibold text-green-600">
                    <TrendingUpIcon className="h-3.5 w-3.5" />
                    良かった点
                  </div>
                  <p className="text-base leading-relaxed text-muted-foreground">
                    {feedback.strength}
                  </p>
                </div>
              )}

              {feedback.improvements && (
                <div>
                  <div className="mb-1 flex items-center gap-1 text-xs font-semibold text-amber-600">
                    <AlertCircleIcon className="h-3.5 w-3.5" />
                    改善点
                  </div>
                  <p className="text-base leading-relaxed text-muted-foreground">
                    {feedback.improvements}
                  </p>
                </div>
              )}

              <Button asChild variant="link" className="w-full">
                <Link href={`/notes/${noteId}`}>ノートに戻る</Link>
              </Button>
            </div>
          )}

          {isSessionEnded && !feedback && (
            <div className="mx-auto max-w-md rounded-xl border bg-card p-6 text-center">
              <p className="text-sm text-muted-foreground">
                復習セッションが終了しました
              </p>
              <Button asChild variant="link" className="mt-2">
                <Link href={`/notes/${noteId}`}>ノートに戻る</Link>
              </Button>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {!isSessionEnded && (
        <div className="shrink-0 bg-background/95 backdrop-blur-sm px-6 py-4">
          <div className="mx-auto max-w-3xl">
            <ChatInput
              value={input}
              onChange={setInput}
              onSend={handleSendMessage}
              isLoading={isLoading}
            />
          </div>
        </div>
      )}
    </div>
  );
}
