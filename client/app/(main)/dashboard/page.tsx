"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { authClient } from "@/lib/auth-client";
import { fetchAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import {
  PlusIcon,
  BookOpenIcon,
  RotateCcwIcon,
  ClockIcon,
  SparklesIcon,
  TrendingUpIcon,
} from "lucide-react";

interface ReviewSchedule {
  id: string;
  note_id: string;
  review_count: number;
  next_review_at: string;
  note_topic: string;
  note_summary: string;
}

type Urgency = "overdue" | "today" | "tomorrow" | "later";

function getUrgency(nextReviewAt: string): Urgency {
  const reviewDate = new Date(nextReviewAt);
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const tomorrowStart = new Date(todayStart);
  tomorrowStart.setDate(tomorrowStart.getDate() + 1);
  const dayAfterStart = new Date(tomorrowStart);
  dayAfterStart.setDate(dayAfterStart.getDate() + 1);

  if (reviewDate < todayStart) return "overdue";
  if (reviewDate < tomorrowStart) return "today";
  if (reviewDate < dayAfterStart) return "tomorrow";
  return "later";
}

const URGENCY_CONFIG: Record<
  Urgency,
  { label: string; borderClass: string; labelClass: string }
> = {
  overdue: {
    label: "期限切れ",
    borderClass: "border-l-red-500",
    labelClass: "text-red-500",
  },
  today: {
    label: "今日",
    borderClass: "border-l-orange-500",
    labelClass: "text-orange-500",
  },
  tomorrow: {
    label: "明日",
    borderClass: "border-l-amber-400",
    labelClass: "text-amber-500",
  },
  later: {
    label: "それ以降",
    borderClass: "border-l-emerald-500",
    labelClass: "text-emerald-600",
  },
};

export default function DashBoard() {
  const { data: session, isPending } = authClient.useSession();
  const [reviews, setReviews] = useState<ReviewSchedule[]>([]);
  const [completedToday, setCompletedToday] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!session) return;
    fetchAPI<{ review_schedules: ReviewSchedule[]; completed_today: number }>(
      "/api/review-schedules",
    )
      .then(({ review_schedules, completed_today }) => {
        setReviews(review_schedules);
        setCompletedToday(completed_today);
      })
      .catch(() => {
        setReviews([]);
        setCompletedToday(0);
      })
      .finally(() => setIsLoading(false));
  }, [session]);

  const pendingCount = reviews.length;
  const totalCount = pendingCount + completedToday;
  const progressPercent =
    totalCount > 0 ? (completedToday / totalCount) * 100 : 0;
  const allDone = totalCount > 0 && pendingCount === 0;

  if (isPending || isLoading) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-6 flex items-start justify-between">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-9 w-44 rounded-lg" />
        </div>
        <Skeleton className="mb-6 h-24 w-full rounded-xl" />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl border bg-card p-5 space-y-3">
              <div className="flex items-center gap-2">
                <Skeleton className="h-4 w-4 rounded" />
                <Skeleton className="h-5 w-3/5" />
              </div>
              <Skeleton className="h-4 w-4/5 ml-6" />
              <Skeleton className="h-3 w-2/5 ml-6" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!session) return null;

  const today = new Date().toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  });

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="mb-6 flex items-start justify-between">
        <div className="border-l-4 border-blue-500 pl-4">
          <p className="mb-1 text-xs font-semibold tracking-widest text-blue-500">
            DAILY REVIEW
          </p>
          <h1 className="text-2xl font-bold">今日の復習</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {pendingCount > 0
              ? `${pendingCount} 件のノートが復習待ちです`
              : "復習待ちのノートはありません"}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-3">
          <p className="text-sm text-muted-foreground">{today}</p>
          <Button
            asChild
            className="gap-2 bg-blue-600 text-white shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-blue-500 hover:shadow-lg hover:shadow-blue-500/30 [a]:hover:bg-blue-500 active:translate-y-0 active:shadow-sm"
          >
            <Link href="/learn">
              <PlusIcon className="h-5 w-5 transition-transform duration-200 group-hover/button:rotate-90" />
              新規学習
            </Link>
          </Button>
        </div>
      </div>

      {totalCount > 0 && (
        <div className="mb-6 rounded-xl border bg-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-sm font-medium">
              <TrendingUpIcon className="h-4 w-4 text-blue-500" />
              進捗
            </span>
            <span className="text-sm text-muted-foreground">
              {completedToday} / {totalCount} 件完了
            </span>
          </div>
          <Progress
            value={progressPercent}
            className="h-2 [&>div]:bg-blue-500"
          />
          {allDone && (
            <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-emerald-600">
              <SparklesIcon className="h-3.5 w-3.5" />
              今日の復習をすべて完了しました！
            </p>
          )}
        </div>
      )}

      <section>
        <div className="mb-4 flex items-center gap-2">
          <RotateCcwIcon className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">復習</h2>
          {pendingCount > 0 && (
            <Badge variant="destructive" className="ml-1">
              {pendingCount}
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
            {reviews.map((review) => {
              const urgency = getUrgency(review.next_review_at);
              const { borderClass, label, labelClass } =
                URGENCY_CONFIG[urgency];

              return (
                <div
                  key={review.id}
                  className={`group rounded-xl border border-l-4 bg-card transition-all duration-200 hover:border-foreground/20 hover:shadow-lg hover:-translate-y-0.5 ${borderClass}`}
                >
                  <Link href={`/notes/${review.note_id}`} className="block p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <div className="mb-1 flex items-center gap-2">
                          <BookOpenIcon className="h-4 w-4 text-primary shrink-0" />
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
                      <Badge variant="warning" className="shrink-0 gap-1">
                        <RotateCcwIcon className="h-3 w-3" />
                        {review.review_count}
                        <span>回目</span>
                      </Badge>
                    </div>
                    <div className="mt-3 flex items-center gap-3 pl-6 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <ClockIcon className="h-3 w-3" />
                        {new Date(review.next_review_at).toLocaleDateString(
                          "ja-JP",
                        )}
                        までに復習
                      </span>
                      <span className={`font-medium ${labelClass}`}>
                        {label}
                      </span>
                    </div>
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
