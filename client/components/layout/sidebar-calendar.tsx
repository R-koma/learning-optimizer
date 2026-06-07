"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ja } from "date-fns/locale";
import { format } from "date-fns";
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import { fetchAPI } from "@/lib/api";
import { cn } from "@/lib/utils";
import { groupNotesByDate, toLocalDateKey } from "@/lib/group-notes-by-date";
import {
  addMonths,
  buildCalendarWeeks,
  isSameDay,
  startOfMonth,
} from "@/lib/calendar-grid";
import { Skeleton } from "@/components/ui/skeleton";

interface CalendarNote {
  id: string;
  topic: string;
  created_at: string;
}

interface CalendarReview {
  id: string;
  note_id: string;
  note_topic: string;
  next_review_at: string;
}

interface DayEntry {
  key: string;
  href: string;
  topic: string;
}

const WEEKDAYS = ["日", "月", "火", "水", "木", "金", "土"] as const;

export function SidebarCalendar() {
  const [notes, setNotes] = useState<CalendarNote[]>([]);
  const [reviews, setReviews] = useState<CalendarReview[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [viewDate, setViewDate] = useState(() => startOfMonth(new Date()));
  const [selected, setSelected] = useState<Date | null>(null);

  // 親が expanded のときだけマウントされるため、初回展開時に一度だけ取得される。
  // 学習（過去のノート）と未来の復習予定をまとめて読み、振り返り兼プランナーにする
  useEffect(() => {
    let active = true;
    Promise.all([
      fetchAPI<{ notes: CalendarNote[] }>("/api/notes").catch(() => ({
        notes: [],
      })),
      fetchAPI<{ review_schedules: CalendarReview[] }>(
        "/api/review-schedules/upcoming",
      ).catch(() => ({ review_schedules: [] })),
    ])
      .then(([noteRes, reviewRes]) => {
        if (!active) return;
        setNotes(noteRes.notes);
        setReviews(reviewRes.review_schedules);
      })
      .finally(() => active && setIsLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const notesByDate = useMemo(() => groupNotesByDate(notes), [notes]);
  const reviewsByDate = useMemo(() => {
    const map = new Map<string, CalendarReview[]>();
    for (const review of reviews) {
      const key = toLocalDateKey(new Date(review.next_review_at));
      const existing = map.get(key);
      if (existing) existing.push(review);
      else map.set(key, [review]);
    }
    return map;
  }, [reviews]);

  const weeks = useMemo(() => buildCalendarWeeks(viewDate), [viewDate]);
  const today = useMemo(() => new Date(), []);
  const todayKey = toLocalDateKey(today);
  // 当月（実際の今月）を表示しているときだけ月ラベルを強調し、別の月へ移動したと分かるようにする
  const isViewingCurrentMonth =
    viewDate.getFullYear() === today.getFullYear() &&
    viewDate.getMonth() === today.getMonth();

  const selectedKey = selected ? toLocalDateKey(selected) : null;
  const selectedNotes = selectedKey ? (notesByDate.get(selectedKey) ?? []) : [];
  const selectedReviews = selectedKey
    ? (reviewsByDate.get(selectedKey) ?? [])
    : [];

  const handleSelect = (date: Date) => {
    setSelected(date);
    // 前後の月のマスを押したらその月へ送る
    setViewDate(startOfMonth(date));
  };

  const noteEntries: DayEntry[] = selectedNotes.map((note) => ({
    key: note.id,
    href: `/notes/${note.id}`,
    topic: note.topic,
  }));
  const reviewEntries: DayEntry[] = selectedReviews.map((review) => ({
    key: review.id,
    href: `/notes/${review.note_id}`,
    topic: review.note_topic,
  }));

  const renderSection = (
    label: string,
    entries: DayEntry[],
    variant: "learned" | "review",
  ) => (
    <div>
      <p className="mb-1 px-1 text-[0.7rem] font-medium text-muted-foreground/70">
        {label}
      </p>
      <ul className="space-y-1">
        {entries.map((entry) => (
          <li key={entry.key}>
            <Link
              href={entry.href}
              className="group flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors hover:bg-muted"
              title={entry.topic}
            >
              <span
                className={cn(
                  "size-1.5 shrink-0 rounded-full",
                  variant === "learned"
                    ? "bg-primary"
                    : "border border-primary",
                )}
              />
              <span className="truncate text-xs group-hover:text-primary">
                {entry.topic}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );

  if (isLoading) {
    return <Skeleton className="h-64 w-full rounded-xl" />;
  }

  return (
    <div className="@container mx-auto w-full max-w-[280px]">
      <div className="mb-3 px-1">
        <div className="flex items-center justify-between gap-1">
          <button
            type="button"
            aria-label="前の月"
            onClick={() => setViewDate((d) => addMonths(d, -1))}
            className="inline-flex size-7 shrink-0 cursor-pointer items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <ChevronLeftIcon className="size-4" />
          </button>
          <div className="flex flex-col items-center">
            <span className="text-sm font-semibold">
              {format(viewDate, "yyyy年 M月", { locale: ja })}
            </span>
            {/* 当月表示時のみアクセント下線を出す。非表示時も高さを確保してレイアウトのずれを防ぐ */}
            <span
              className={cn(
                "mt-0.5 h-0.5 w-full rounded-full transition-colors",
                isViewingCurrentMonth ? "bg-primary" : "bg-transparent",
              )}
            />
          </div>
          <button
            type="button"
            aria-label="次の月"
            onClick={() => setViewDate((d) => addMonths(d, 1))}
            className="inline-flex size-7 shrink-0 cursor-pointer items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <ChevronRightIcon className="size-4" />
          </button>
        </div>
        {!isViewingCurrentMonth && (
          <div className="mt-1 flex justify-center">
            <button
              type="button"
              onClick={() => setViewDate(startOfMonth(today))}
              className="cursor-pointer rounded-full border px-2 py-0.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              今日
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-7">
        {WEEKDAYS.map((w) => (
          <div
            key={w}
            className="pb-1.5 text-center text-[0.7rem] font-medium text-muted-foreground/70"
          >
            {w}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-0.5">
        {weeks.flat().map(({ date, inCurrentMonth }) => {
          const key = toLocalDateKey(date);
          const isSelected = selected !== null && isSameDay(date, selected);
          const isToday = isSameDay(date, today);
          const isLearned = notesByDate.has(key);
          const hasReview = reviewsByDate.has(key);
          // 過去日（記録なしも閲覧可）と、見せるものがある日（学習/復習予定）のみ操作可能。
          // 本日以降で予定が無い日は色を通常のまま据え置き、クリックしても何もしない
          const isInteractive = key < todayKey || isLearned || hasReview;

          return (
            <button
              key={date.getTime()}
              type="button"
              tabIndex={isInteractive ? undefined : -1}
              onClick={isInteractive ? () => handleSelect(date) : undefined}
              className={cn(
                // 既定色はサイドバーの非アクティブ項目と同じ text-muted-foreground にそろえる
                "relative mx-auto flex aspect-square w-full items-center justify-center rounded-full text-xs text-muted-foreground transition-colors @[17rem]:text-sm",
                !inCurrentMonth && "text-muted-foreground/40",
                isInteractive ? "cursor-pointer" : "cursor-default",
                isInteractive && !isSelected && "hover:bg-muted",
                // 今日: 円形のリングで縁取り（選択日の塗りつぶしと区別する）
                isToday &&
                  !isSelected &&
                  "font-semibold text-primary ring-1 ring-inset ring-primary/50",
                isSelected &&
                  "bg-primary font-semibold text-primary-foreground hover:bg-primary",
              )}
            >
              {date.getDate()}
              {(isLearned || hasReview) && (
                <span className="absolute bottom-1 left-1/2 flex -translate-x-1/2 items-center gap-0.5">
                  {isLearned && (
                    <span
                      className={cn(
                        "size-1 rounded-full",
                        isSelected ? "bg-primary-foreground" : "bg-primary",
                      )}
                    />
                  )}
                  {hasReview && (
                    <span
                      className={cn(
                        "size-1 rounded-full border",
                        isSelected
                          ? "border-primary-foreground"
                          : "border-primary",
                      )}
                    />
                  )}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="mt-2 flex items-center justify-center gap-3 text-[0.65rem] text-muted-foreground/70">
        <span className="flex items-center gap-1">
          <span className="size-1.5 rounded-full bg-primary" />
          学習
        </span>
        <span className="flex items-center gap-1">
          <span className="size-1.5 rounded-full border border-primary" />
          復習予定
        </span>
      </div>

      {selected && (
        <div className="mt-3 border-t pt-3">
          <div className="mb-2 flex items-center justify-between px-1">
            <span className="text-xs font-semibold">
              {format(selected, "M月d日 (E)", { locale: ja })}
            </span>
            {noteEntries.length + reviewEntries.length > 0 && (
              <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[0.65rem] font-medium text-primary">
                {noteEntries.length + reviewEntries.length}
              </span>
            )}
          </div>
          {noteEntries.length === 0 && reviewEntries.length === 0 ? (
            <p className="px-1 text-xs text-muted-foreground/70">
              この日の学習記録はありません
            </p>
          ) : (
            <div className="space-y-2">
              {noteEntries.length > 0 &&
                renderSection("学習", noteEntries, "learned")}
              {reviewEntries.length > 0 &&
                renderSection("復習予定", reviewEntries, "review")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
