"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useChatWebSocket, type TargetDepth } from "@/hooks/use-chat-websocket";
import { fetchAPI } from "@/lib/api";
import { useNavbarSlot } from "@/context/navbar-slot-context";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ChatInput } from "@/components/chat/chat-input";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRightIcon,
  BookOpenIcon,
  CheckIcon,
  HistoryIcon,
  Loader2Icon,
  MessageCircleIcon,
  NotebookPenIcon,
  PencilIcon,
  FlagIcon,
  PlusIcon,
  RocketIcon,
  SparklesIcon,
  XIcon,
} from "lucide-react";

const TARGET_DEPTH_OPTIONS: {
  value: TargetDepth;
  label: string;
  hint: string;
  icon: LucideIcon;
}[] = [
  {
    value: "recognize",
    label: "概要",
    hint: "言葉の意味と全体像が分かる",
    icon: BookOpenIcon,
  },
  {
    value: "explain",
    label: "説明",
    hint: "他人に教えられる、具体例を出せる",
    icon: MessageCircleIcon,
  },
  {
    value: "apply",
    label: "実践応用",
    hint: "具体的な場面で使える、応用展開できる",
    icon: RocketIcon,
  },
];

interface ActiveSessionResponse {
  session_id: string;
  session_type: "learning" | "review";
  status: string;
  started_at: string;
  topic: string | null;
}

interface SessionMessageItem {
  role: "user" | "assistant";
  content: string;
  message_order: number;
}

interface SessionMessagesResponse {
  session_id: string;
  session_type: "learning" | "review";
  status: string;
  note_id: string | null;
  messages: SessionMessageItem[];
}

export default function LearnPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionParam = searchParams.get("session");
  const [topic, setTopic] = useState("");
  const [learningGoal, setLearningGoal] = useState("");
  const [targetDepth, setTargetDepth] = useState<TargetDepth | null>(null);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [resumableSession, setResumableSession] =
    useState<ActiveSessionResponse | null>(null);
  const restoredSessionRef = useRef<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { setNavbarCenter } = useNavbarSlot();

  const {
    messages,
    isConnected,
    isLoading,
    isSessionEnded,
    isGeneratingNote,
    generatedNote,
    error,
    editingMessage,
    sessionId,
    startLearning,
    resumeSession,
    sendMessage,
    endSession,
    cancelLastMessage,
    clearEditingMessage,
    resetSession,
  } = useChatWebSocket();

  useEffect(() => {
    if (sessionParam) {
      if (restoredSessionRef.current === sessionParam) return;
      restoredSessionRef.current = sessionParam;
      setIsBootstrapping(true);
      setResumableSession(null);

      (async () => {
        try {
          const data = await fetchAPI<SessionMessagesResponse>(
            `/api/dialogue-sessions/${sessionParam}/messages`,
          );
          if (data.status !== "in_progress" && data.status !== "disconnect") {
            return;
          }
          const initialMessages = data.messages.map(({ role, content }) => ({
            role,
            content,
          }));
          if (data.session_type === "learning" && initialMessages.length > 0) {
            setTopic(initialMessages[0].content);
          }
          resumeSession(
            sessionParam,
            data.session_type === "learning"
              ? initialMessages.slice(1)
              : initialMessages,
          );
        } catch {
          // セッションが無効化 / 404 の場合は新規開始フローに戻す
        } finally {
          setIsBootstrapping(false);
        }
      })();
      return;
    }

    restoredSessionRef.current = null;
    resetSession();
    /* eslint-disable react-hooks/set-state-in-effect */
    setTopic("");
    setLearningGoal("");
    setTargetDepth(null);
    setIsDetailsOpen(false);
    setInput("");
    setIsBootstrapping(true);
    /* eslint-enable react-hooks/set-state-in-effect */
    fetchAPI<ActiveSessionResponse | null>("/api/dialogue-sessions/active")
      .then((res) => {
        if (res?.session_id) {
          setResumableSession(res);
        } else {
          setResumableSession(null);
        }
      })
      .catch(() => {
        // 取得失敗時は再開バナーを出さずに新規学習フォームを表示する
      })
      .finally(() => setIsBootstrapping(false));
  }, [sessionParam, resumeSession, resetSession]);

  useEffect(() => {
    if (!sessionId) return;
    if (sessionParam === sessionId) return;
    restoredSessionRef.current = sessionId;
    router.replace(`/learn?session=${sessionId}`);
  }, [sessionId, sessionParam, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    if (!generatedNote) return;
    router.push(`/notes/${generatedNote.note_id}`);
  }, [generatedNote, router]);

  if (editingMessage !== null) {
    setInput(editingMessage);
    clearEditingMessage();
  }

  useEffect(() => {
    if (isConnected && topic) {
      setNavbarCenter(
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-semibold">{topic}</h1>
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
          </div>
        </div>,
      );
    } else {
      setNavbarCenter(null);
    }
    return () => setNavbarCenter(null);
  }, [isConnected, topic, endSession, router, setNavbarCenter]);

  const handleStartLearning = () => {
    if (!topic.trim()) return;

    startLearning(topic.trim(), {
      learning_goal: learningGoal.trim() || undefined,
      target_depth: targetDepth ?? undefined,
    });
  };

  const handleSendMessage = (content: string) => {
    if (!content.trim()) return;
    sendMessage(content);
    setInput("");
  };

  if (isBootstrapping) {
    return (
      <div className="flex h-full flex-col">
        <div className="flex-1 space-y-4 p-4 overflow-hidden">
          <div className="flex justify-start">
            <Skeleton className="h-16 w-2/3 rounded-2xl" />
          </div>
          <div className="flex justify-end">
            <Skeleton className="h-16 w-1/2 rounded-2xl" />
          </div>
          <div className="flex justify-start">
            <Skeleton className="h-16 w-3/5 rounded-2xl" />
          </div>
        </div>
        <div className="border-t p-4">
          <Skeleton className="h-12 w-full rounded-xl" />
        </div>
      </div>
    );
  }

  if (messages.length === 0 && !isConnected) {
    return (
      <div className="flex h-full items-center justify-center overflow-y-auto p-4">
        <div className="w-full max-w-lg my-4 space-y-4">
          {resumableSession && (
            <div className="group relative overflow-hidden rounded-2xl border border-primary/20 bg-liner-to-br from-primary/8 via-background to-background p-5 shadow-sm transition-all hover:border-primary/40 hover:shadow-md">
              <div className="pointer-events-none absolute -top-12 -right-12 h-32 w-32 rounded-full bg-primary/10 blur-3xl" />

              <div className="relative flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 text-primary">
                    <HistoryIcon className="h-3.5 w-3.5" />
                  </div>
                  <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    前回の会話
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={async () => {
                    const target = resumableSession;
                    setResumableSession(null);
                    try {
                      await fetchAPI(
                        `/api/dialogue-sessions/${target.session_id}`,
                        { method: "DELETE" },
                      );
                    } catch {
                      setResumableSession(target);
                    }
                  }}
                  className="-mt-1 -mr-1 h-7 w-7 shrink-0 cursor-pointer rounded-full text-muted-foreground opacity-60 transition-opacity hover:bg-background hover:text-foreground hover:opacity-100"
                  title="前回の会話を削除"
                >
                  <XIcon className="h-3.5 w-3.5" />
                </Button>
              </div>

              <button
                type="button"
                onClick={() =>
                  router.push(`/learn?session=${resumableSession.session_id}`)
                }
                className="group/btn relative mt-3 flex w-full items-center justify-between gap-4 text-left cursor-pointer"
              >
                <p className="line-clamp-2 text-lg font-semibold leading-snug text-foreground">
                  {resumableSession.topic ?? "（タイトル未設定）"}
                </p>
                <span className="flex shrink-0 items-center gap-1.5 rounded-full bg-primary px-3.5 py-1.5 text-xs font-medium text-primary-foreground shadow-sm transition-transform group-hover/btn:translate-x-0.5">
                  続きから再開
                  <ArrowRightIcon className="h-3.5 w-3.5" />
                </span>
              </button>
            </div>
          )}
          <div className="relative overflow-hidden rounded-2xl border border-primary/20 bg-linear-to-br from-primary/8 via-background to-background p-8 shadow-sm">
            <div className="pointer-events-none absolute -top-16 -right-16 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-20 -left-20 h-40 w-40 rounded-full bg-primary/5 blur-3xl" />

            <div className="relative">
              <div className="mb-6 flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-linear-to-br from-primary to-primary/70 text-primary-foreground shadow-sm shadow-primary/20">
                  <SparklesIcon className="h-4 w-4" />
                </div>
                <h1 className="text-xl font-bold tracking-tight text-foreground">
                  新規学習
                </h1>
              </div>

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleStartLearning();
                }}
              >
                <div className="flex flex-col gap-6">
                  <div>
                    <Input
                      id="topic"
                      type="text"
                      placeholder="学びたいトピックを入力"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      className="h-12 rounded-xl border-input/60 bg-background/60 text-base shadow-sm backdrop-blur transition-colors focus-visible:border-primary/60"
                      required
                    />
                  </div>

                  <div className="grid gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-foreground">
                        習熟レベル
                      </span>
                      <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                        任意
                      </span>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-3">
                      {TARGET_DEPTH_OPTIONS.map((option) => {
                        const isSelected = targetDepth === option.value;
                        const Icon = option.icon;
                        return (
                          <button
                            key={option.value}
                            type="button"
                            onClick={() =>
                              setTargetDepth(isSelected ? null : option.value)
                            }
                            className={`group/opt relative flex cursor-pointer flex-col gap-3 rounded-xl border p-4 text-left transition-all focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:outline-none ${
                              isSelected
                                ? "border-primary/60 bg-primary/10 shadow-sm ring-1 ring-primary/15"
                                : "border-input/60 bg-background/45 hover:border-primary/30 hover:bg-background/80 hover:shadow-sm"
                            }`}
                          >
                            <span className="flex items-center gap-2">
                              <Icon
                                className={`h-3.5 w-3.5 shrink-0 transition-colors ${
                                  isSelected
                                    ? "text-primary"
                                    : "text-muted-foreground group-hover/opt:text-primary"
                                }`}
                              />
                              <span className="flex-1 text-sm font-semibold tracking-tight text-foreground">
                                {option.label}
                              </span>
                              <span
                                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors ${
                                  isSelected
                                    ? "border-primary bg-primary text-primary-foreground"
                                    : "border-input/80 bg-background/80"
                                }`}
                              >
                                {isSelected && (
                                  <CheckIcon
                                    className="h-3 w-3"
                                    strokeWidth={3}
                                  />
                                )}
                              </span>
                            </span>
                            <span className="text-xs leading-relaxed text-muted-foreground">
                              {option.hint}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div>
                    {isDetailsOpen ? (
                      <div className="rounded-xl border border-input/60 bg-background/60 shadow-sm backdrop-blur">
                        <div className="flex items-center justify-between px-4 pt-4 pb-2">
                          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            <FlagIcon className="h-3.5 w-3.5 shrink-0" />
                            学習を通じて達成したいゴール
                          </span>
                          <button
                            type="button"
                            onClick={() => {
                              setIsDetailsOpen(false);
                              setLearningGoal("");
                            }}
                            className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                          >
                            <XIcon className="h-3.5 w-3.5" />
                          </button>
                        </div>
                        <Textarea
                          id="learning-goal"
                          autoFocus
                          value={learningGoal}
                          onChange={(e) => setLearningGoal(e.target.value)}
                          className="min-h-20 resize-none border-0 bg-transparent px-4 pb-4 pt-2 text-sm shadow-none focus-visible:ring-0"
                        />
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setIsDetailsOpen(true)}
                        className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                      >
                        <PlusIcon className="h-3.5 w-3.5" />
                        学習ゴールを追加
                      </button>
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={!topic.trim()}
                    className="group/cta mt-2 flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary text-base font-medium text-primary-foreground shadow-sm transition-all cursor-pointer hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    学習を開始する
                    <ArrowRightIcon className="h-4 w-4 transition-transform group-hover/cta:translate-x-0.5" />
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
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
                  className={`max-w-full rounded-2xl px-4 py-3 text-base leading-relaxed whitespace-pre-wrap ${
                    msg.role === "user" ? "bg-muted" : ""
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

          {isSessionEnded && !generatedNote && !isGeneratingNote && (
            <div className="mx-auto max-w-md rounded-lg border p-4 text-center">
              <p className="text-sm text-muted-foreground">
                セッションが終了しました
              </p>
              <Button asChild variant="link" className="mt-2">
                <Link href="/dashboard">ダッシュボードに戻る</Link>
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

      {isGeneratingNote && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs">
          <div className="flex flex-col items-center gap-4 rounded-xl border bg-background px-8 py-6 shadow-lg">
            <Loader2Icon className="h-8 w-8 animate-spin text-primary" />
            <p className="text-base font-medium">ノート作成中...</p>
          </div>
        </div>
      )}
    </div>
  );
}
