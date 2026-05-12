"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useChatWebSocket, type TargetDepth } from "@/hooks/use-chat-websocket";
import { fetchAPI } from "@/lib/api";
import { useNavbarSlot } from "@/context/navbar-slot-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ChatInput } from "@/components/chat/chat-input";
import {
  ArrowRightIcon,
  CheckIcon,
  ChevronDownIcon,
  HistoryIcon,
  Loader2Icon,
  NotebookPenIcon,
  PencilIcon,
  SparklesIcon,
  XIcon,
} from "lucide-react";

const TARGET_DEPTH_OPTIONS: {
  value: TargetDepth;
  label: string;
  hint: string;
}[] = [
  {
    value: "recognize",
    label: "概要を掴みたい",
    hint: "言葉の意味と全体像が分かる",
  },
  {
    value: "explain",
    label: "自分の言葉で説明できる",
    hint: "他人に教えられる、具体例を出せる",
  },
  {
    value: "apply",
    label: "実践・応用できる",
    hint: "具体的な場面で使える、応用展開できる",
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
          resumeSession(sessionParam, initialMessages);
        } catch {
          // セッションが無効化 / 404 の場合は新規開始フローに戻す
        } finally {
          setIsBootstrapping(false);
        }
      })();
      return;
    }

    restoredSessionRef.current = null;
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
  }, [sessionParam, resumeSession]);

  useEffect(() => {
    if (!sessionId) return;
    if (sessionParam === sessionId) return;
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
      <div className="flex h-full items-center justify-center">
        <Loader2Icon className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (messages.length === 0 && !isConnected) {
    return (
      <div className="flex h-full items-center justify-center overflow-y-auto p-4">
        <div className="w-full max-w-lg my-4 space-y-4">
          {resumableSession && (
            <div className="group relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/8 via-background to-background p-5 shadow-sm transition-all hover:border-primary/40 hover:shadow-md">
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
          <div className="relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/8 via-background to-background p-8 shadow-sm">
            <div className="pointer-events-none absolute -top-16 -right-16 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-20 -left-20 h-40 w-40 rounded-full bg-primary/5 blur-3xl" />

            <div className="relative">
              <div className="mb-6 flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/70 text-primary-foreground shadow-sm shadow-primary/20">
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
                  <div className="grid gap-2">
                    <Label
                      htmlFor="topic"
                      className="text-xs font-medium tracking-wide text-muted-foreground uppercase"
                    >
                      トピック
                    </Label>
                    <Input
                      id="topic"
                      type="text"
                      placeholder="例: TCP/IP、二分探索木、デザインパターン"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      className="h-12 rounded-xl border-input/60 bg-background/60 text-base shadow-sm backdrop-blur transition-colors focus-visible:border-primary/60"
                      required
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label className="flex items-baseline gap-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                      到達したいレベル
                      <span className="text-[10px] font-normal normal-case tracking-normal">
                        （任意）
                      </span>
                    </Label>
                    <div className="grid gap-2">
                      {TARGET_DEPTH_OPTIONS.map((option) => {
                        const isSelected = targetDepth === option.value;
                        return (
                          <button
                            key={option.value}
                            type="button"
                            onClick={() =>
                              setTargetDepth(isSelected ? null : option.value)
                            }
                            className={`group/opt relative flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all cursor-pointer ${
                              isSelected
                                ? "border-primary/60 bg-primary/8 shadow-sm"
                                : "border-input/60 bg-background/40 hover:border-primary/30 hover:bg-background/80"
                            }`}
                          >
                            <span
                              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors ${
                                isSelected
                                  ? "border-primary bg-primary text-primary-foreground"
                                  : "border-input/80 bg-background"
                              }`}
                            >
                              {isSelected && (
                                <CheckIcon
                                  className="h-3 w-3"
                                  strokeWidth={3}
                                />
                              )}
                            </span>
                            <span className="flex flex-col gap-0.5">
                              <span className="text-sm font-medium">
                                {option.label}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {option.hint}
                              </span>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="grid gap-2">
                    <button
                      type="button"
                      onClick={() => setIsDetailsOpen((v) => !v)}
                      className="flex items-center gap-1.5 self-start text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                      aria-expanded={isDetailsOpen}
                    >
                      <ChevronDownIcon
                        className={`h-4 w-4 transition-transform ${
                          isDetailsOpen ? "rotate-0" : "-rotate-90"
                        }`}
                      />
                      詳細を追加（任意）
                    </button>
                    {isDetailsOpen && (
                      <div className="grid gap-2 pt-1">
                        <Label
                          htmlFor="learning-goal"
                          className="text-xs font-medium tracking-wide text-muted-foreground uppercase"
                        >
                          学習ゴール
                        </Label>
                        <Textarea
                          id="learning-goal"
                          placeholder="例: ReAct で Tool 呼び出しの設計パターンを理解したい"
                          value={learningGoal}
                          onChange={(e) => setLearningGoal(e.target.value)}
                          className="min-h-16 rounded-xl border-input/60 bg-background/60 text-sm shadow-sm backdrop-blur transition-colors focus-visible:border-primary/60"
                        />
                      </div>
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
