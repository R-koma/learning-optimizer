"use client";

import { useRef, useEffect, useState } from "react";
import Link from "next/link";
import { useChatWebSocket } from "@/hooks/use-chat-websocket";
import { ScrollArea } from "@/components/ui/scroll-area";
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
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export default function LearnPage() {
  const [topic, setTopic] = useState("");
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    isConnected,
    isLoading,
    isSessionEnded,
    generatedNote,
    error,
    startLearning,
    sendMessage,
    endSession,
  } = useChatWebSocket();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleStartLearning = () => {
    if (!topic.trim()) return;
    startLearning(topic.trim());
  };

  const handleSendMessage = () => {
    if (!input.trim()) return;
    sendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (messages.length === 0 && !isConnected) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-lg shadow-lg">
          <CardHeader className="space-y-2 px-8 pt-10 pb-4">
            <CardTitle className="text-center text-2xl font-bold">
              新規学習
            </CardTitle>
            <p className="text-center text-sm text-muted-foreground">
              学習したいトピックを入力して開始しましょう
            </p>
          </CardHeader>
          <CardContent className="px-8 pb-4">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleStartLearning();
              }}
            >
              <div className="flex flex-col gap-4">
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
    <div className="flex h-screen flex-col">
      <div className="border-b px-6 py-3">
        <h1 className="text-lg font-semibold">{topic}</h1>
      </div>

      {error && (
        <div className="px-6 py-2 text-sm text-destructive">{error}</div>
      )}

      <ScrollArea className="flex-1 px-6">
        <div className="mx-auto max-w-3xl space-y-4 py-6">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex items-start gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              <Avatar className="mt-1 shrink-0">
                <AvatarFallback>
                  {msg.role === "user" ? "You" : "AI"}
                </AvatarFallback>
              </Avatar>
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-3 text-base leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex items-start gap-3">
              <Avatar className="mt-1 shrink-0">
                <AvatarFallback>AI</AvatarFallback>
              </Avatar>
              <div className="rounded-2xl bg-muted px-4 py-3 text-sm text-muted-foreground">
                考え中...
              </div>
            </div>
          )}

          {generatedNote && (
            <div className="mx-auto max-w-md rounded-lg border p-4 text-center">
              <h2 className="mb-2 font-semibold">ノートが生成されました</h2>
              <p className="text-sm text-muted-foreground">
                {generatedNote.topic}
              </p>
              <p className="mt-1 text-sm">{generatedNote.summary}</p>
              <Button asChild variant="link" className="mt-2">
                <Link href={`/notes/${generatedNote.note_id}`}>
                  ノートを見る
                </Link>
              </Button>
            </div>
          )}

          {isSessionEnded && (
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
      </ScrollArea>

      {!isSessionEnded && (
        <div className="border-t px-6 py-4">
          <div className="mx-auto flex max-w-3xl items-center gap-3">
            <Textarea
              placeholder="回答を入力..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              className="min-h-10 flex-1 resize-none"
              rows={1}
            />
            <Button
              onClick={endSession}
              variant="outline"
              className="shrink-0 hover:bg-black hover:text-white cursor-pointer"
            >
              終了
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
