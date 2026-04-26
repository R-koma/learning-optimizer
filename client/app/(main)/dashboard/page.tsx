"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { authClient } from "@/lib/auth-client";
import { fetchAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  PlusIcon,
  BookOpenIcon,
  RotateCcwIcon,
  ClockIcon,
  SparklesIcon,
} from "lucide-react";

interface ReviewSchedule {
  id: string;
  note_id: string;
  review_count: number;
  next_review_at: string;
  note_topic: string;
  note_summary: string;
}

export default function DashBoard() {
  const { data: session, isPending } = authClient.useSession();
  const [reviews, setReviews] = useState<ReviewSchedule[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!session) return;
    fetchAPI<{ review_schedules: ReviewSchedule[] }>("/api/review-schedules")
      .then(({ review_schedules }) => setReviews(review_schedules))
      .catch(() => setReviews([]))
      .finally(() => setIsLoading(false));
  }, [session]);

  if (isPending || isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <p className="text-sm text-muted-foreground">読み込み中...</p>
      </div>
    );
  }

  if (!session) return null;

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">今日の復習</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          学習状況を確認しましょう
        </p>
      </div>

      <div className="mb-8">
        <Button asChild size="lg" className="gap-2">
          <Link href="/learn">
            <PlusIcon className="h-5 w-5" />
            新しい学習を始める
          </Link>
        </Button>
      </div>

      <section>
        <div className="mb-4 flex items-center gap-2">
          <RotateCcwIcon className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">復習</h2>
          {reviews.length > 0 && (
            <Badge variant="destructive" className="ml-1">
              {reviews.length}
            </Badge>
          )}
        </div>

        {reviews.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border bg-card py-16 text-center">
            <SparklesIcon className="mb-4 h-10 w-10 text-muted-foreground/30" />
            <p className="text-sm font-medium text-muted-foreground">
              復習が必要なノートはありません
            </p>
            <p className="mt-1 text-xs text-muted-foreground/70">
              学習を続けると、ここに復習スケジュールが表示されます
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {reviews.map((review) => (
              <Link
                key={review.id}
                href={`/notes/${review.note_id}`}
                className="block"
              >
                <div className="group rounded-xl border bg-card p-5 transition-all duration-200 hover:border-foreground/20 hover:shadow-lg hover:-translate-y-0.5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <BookOpenIcon className="h-4 w-4 text-primary" />
                        <span className="truncate font-semibold transition-colors group-hover:text-primary">
                          {review.note_topic}
                        </span>
                      </div>
                      {review.note_summary && (
                        <p className="line-clamp-1 pl-6 text-sm text-muted-foreground">
                          {review.note_summary}
                        </p>
                      )}
                    </div>
                    <Badge variant="outline" className="shrink-0 gap-1">
                      <RotateCcwIcon className="h-3 w-3" />
                      {review.review_count}
                      <span>回目</span>
                    </Badge>
                  </div>
                  <div className="mt-3 flex items-center gap-1 pl-6 text-xs text-muted-foreground">
                    <ClockIcon className="h-3 w-3" />
                    <span>
                      {new Date(review.next_review_at).toLocaleDateString(
                        "ja-JP",
                      )}
                      までに復習
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
