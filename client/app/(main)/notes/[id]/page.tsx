import Link from "next/link";
import { headers } from "next/headers";

export const dynamic = "force-dynamic";
import { fetchAPI, getToken } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Markdown } from "@/components/ui/markdown";
import {
  ArrowLeftIcon,
  BookOpenIcon,
  SparklesIcon,
  FileTextIcon,
  TrendingUpIcon,
  CheckCircleIcon,
  AlertCircleIcon,
  MessageSquareIcon,
  RotateCcwIcon,
} from "lucide-react";

interface Note {
  id: string;
  topic: string;
  content: string;
  summary: string;
}

interface Feedback {
  id: string;
  understanding_level: string;
  strength: string;
  improvements: string;
  created_at: string;
}

export default async function NotePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const cookieHeader = (await headers()).get("cookie") ?? "";
  const token = await getToken(cookieHeader);
  const [note, { feedbacks }] = await Promise.all([
    fetchAPI(`/api/notes/${id}`, { token }) as Promise<Note>,
    fetchAPI(`/api/notes/${id}/feedbacks`, { token }) as Promise<{
      feedbacks: Feedback[];
    }>,
  ]);

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-8">
          <Link
            href="/notes"
            className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeftIcon className="h-4 w-4" />
            学習履歴に戻る
          </Link>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <BookOpenIcon className="h-5 w-5 text-primary" />
              </div>
              <h1 className="text-2xl font-bold">{note.topic}</h1>
            </div>
            <Button asChild className="gap-2">
              <Link href={`/review/${note.id}`}>
                <RotateCcwIcon className="h-4 w-4" />
                復習する
              </Link>
            </Button>
          </div>
        </div>

        <div className="rounded-xl border bg-card p-6">
          <section>
            <div className="mb-4 flex items-center gap-2">
              <MessageSquareIcon className="h-5 w-5 text-foreground" />
              <h2 className="text-lg font-semibold">フィードバック</h2>
            </div>
            {feedbacks.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <MessageSquareIcon className="mb-4 h-10 w-10 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">
                  フィードバックはまだありません
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {feedbacks.map((fb) => (
                  <div key={fb.id}>
                    <div className="mb-4 flex items-center gap-3">
                      <Badge
                        variant="outline"
                        className="gap-1 px-3 py-1 text-sm"
                      >
                        <TrendingUpIcon className="h-3.5 w-3.5" />
                        理解度: {fb.understanding_level}
                      </Badge>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="rounded-lg bg-emerald-500/5 p-4">
                        <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                          <CheckCircleIcon className="h-4 w-4" />
                          強み
                        </div>
                        <p className="text-base leading-relaxed">
                          {fb.strength}
                        </p>
                      </div>
                      <div className="rounded-lg bg-amber-500/5 p-4">
                        <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-amber-600 dark:text-amber-400">
                          <AlertCircleIcon className="h-4 w-4" />
                          改善点
                        </div>
                        <p className="text-base leading-relaxed">
                          {fb.improvements}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <div className="my-6" />

          <section>
            <div className="mb-4 flex items-center gap-2">
              <FileTextIcon className="h-5 w-5 text-foreground" />
              <h2 className="text-lg font-semibold">ノート</h2>
            </div>
            <div className="mb-4 flex items-center gap-2">
              <SparklesIcon className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold uppercase tracking-wider text-primary">
                要約
              </h3>
            </div>
            <Markdown>{note.summary}</Markdown>
            <div className="my-4 flex items-center gap-2">
              <FileTextIcon className="h-4 w-4 text-muted-foreground" />
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                内容
              </h3>
            </div>
            <Markdown>{note.content}</Markdown>
          </section>
        </div>
      </div>
    </div>
  );
}
