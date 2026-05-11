"use client";

import { useRef, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useChatWebSocket, type TargetDepth } from "@/hooks/use-chat-websocket";
import { fetchAPI } from "@/lib/api";
import { useNavbarSlot } from "@/context/navbar-slot-context";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ChatInput } from "@/components/chat/chat-input";
import {
  ChevronDownIcon,
  Loader2Icon,
  NotebookPenIcon,
  PencilIcon,
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
  const bootstrappedRef = useRef(false);
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
    if (bootstrappedRef.current) return;
    bootstrappedRef.current = true;

    const restoreFromSessionId = async (sid: string) => {
      try {
        const data = await fetchAPI<SessionMessagesResponse>(
          `/api/dialogue-sessions/${sid}/messages`,
        );
        if (data.status !== "in_progress" && data.status !== "disconnect") {
          setIsBootstrapping(false);
          return;
        }
        const initialMessages = data.messages.map(({ role, content }) => ({
          role,
          content,
        }));
        if (data.session_type === "learning" && initialMessages.length > 0) {
          setTopic(initialMessages[0].content);
        }
        resumeSession(sid, initialMessages);
      } catch {
        // セッションが無効化 / 404 の場合は新規開始フローに戻す
      } finally {
        setIsBootstrapping(false);
      }
    };

    if (sessionParam) {
      restoreFromSessionId(sessionParam);
      return;
    }

    fetchAPI<ActiveSessionResponse | null>("/api/dialogue-sessions/active")
      .then((res) => {
        if (res?.session_id) {
          router.replace(`/learn?session=${res.session_id}`);
          return;
        }
        setIsBootstrapping(false);
      })
      .catch(() => setIsBootstrapping(false));
  }, [sessionParam, resumeSession, router]);

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
        <Card className="w-full max-w-lg shadow-lg my-4">
          <CardHeader className="space-y-2 px-8 pt-10 pb-4">
            <CardTitle className="text-center text-2xl font-bold">
              新規学習
            </CardTitle>
          </CardHeader>
          <CardContent className="px-8 pb-4">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleStartLearning();
              }}
            >
              <div className="flex flex-col gap-5">
                <div className="grid gap-2">
                  <Label htmlFor="topic" className="text-sm font-medium">
                    トピック
                  </Label>
                  <Input
                    id="topic"
                    type="text"
                    placeholder="例: TCP/IP、二分探索木、デザインパターン"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    className="h-12 text-base"
                    required
                  />
                </div>

                <div className="grid gap-2">
                  <Label className="flex items-baseline gap-2 text-sm font-medium">
                    到達したいレベル
                    <span className="text-xs font-normal text-muted-foreground">
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
                          className={`flex flex-col items-start gap-0.5 rounded-lg border px-3 py-2 text-left transition-colors cursor-pointer ${
                            isSelected
                              ? "border-primary bg-primary/5"
                              : "border-input hover:bg-muted/40"
                          }`}
                        >
                          <span className="text-sm font-medium">
                            {option.label}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {option.hint}
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
                        className="text-sm font-medium"
                      >
                        学習ゴール
                      </Label>
                      <Textarea
                        id="learning-goal"
                        placeholder="例: ReAct で Tool 呼び出しの設計パターンを理解したい"
                        value={learningGoal}
                        onChange={(e) => setLearningGoal(e.target.value)}
                        className="min-h-16 text-sm"
                      />
                    </div>
                  )}
                </div>
              </div>
            </form>
          </CardContent>
          <CardFooter className="px-8 pb-10">
            <Button
              onClick={handleStartLearning}
              className="h-12 w-full text-base cursor-pointer"
            >
              学習を開始する
            </Button>
          </CardFooter>
        </Card>
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
