"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  BookOpenIcon,
  RotateCcwIcon,
  CalendarIcon,
  EllipsisIcon,
} from "lucide-react";
import { fetchAPI } from "@/lib/api";

interface NoteResponse {
  id: string;
  topic: string;
  content: string;
  summary: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  review_count: number;
}

type Filter = "all" | "active" | "archived";

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
}

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "すべて" },
  { value: "archived", label: "完了" },
  { value: "active", label: "進行中" },
];

export function NoteList({ notes }: { notes: NoteResponse[] }) {
  const router = useRouter();
  const [filter, setFilter] = useState<Filter>("all");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);

  const filteredNotes =
    filter === "all" ? notes : notes.filter((note) => note.status === filter);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await fetchAPI(`/api/notes/${id}`, { method: "DELETE" });
      router.refresh();
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div>
      <div className="mb-6 inline-flex rounded-lg border bg-muted p-1">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-all duration-150 cursor-pointer ${
              filter === f.value
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {filteredNotes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <BookOpenIcon className="mb-4 h-10 w-10 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">
            該当するノートがありません
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredNotes.map((note) => (
            <div
              key={note.id}
              className="group relative rounded-xl border bg-card transition-all duration-200 hover:border-foreground/20 hover:shadow-lg hover:-translate-y-0.5"
            >
              <Link href={`/notes/${note.id}`} className="block p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="mb-2 flex items-center gap-2">
                      <span className="truncate font-semibold group-hover:text-primary transition-colors">
                        {note.topic}
                      </span>
                      <Badge
                        variant={
                          note.status === "active" ? "default" : "secondary"
                        }
                        className="shrink-0 "
                      >
                        {note.status === "active" ? "進行中" : "完了"}
                      </Badge>
                    </div>
                    {note.summary && (
                      <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">
                        {note.summary}
                      </p>
                    )}
                  </div>
                </div>
                <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <CalendarIcon className="h-3.5 w-3.5" />
                    {formatDate(note.created_at)}
                  </span>
                  <span className="flex items-center gap-1">
                    <RotateCcwIcon className="h-3.5 w-3.5" />
                    復習回数: {note.review_count}回
                  </span>
                </div>
              </Link>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-3 bottom-3 cursor-pointer"
                    disabled={deletingId === note.id}
                  >
                    <EllipsisIcon className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={() => setDeleteTargetId(note.id)}
                  >
                    削除する
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          ))}
        </div>
      )}

      <AlertDialog
        open={deleteTargetId !== null}
        onOpenChange={(open) => !open && setDeleteTargetId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>ノートを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              「{notes.find((n) => n.id === deleteTargetId)?.topic}
              」を削除します。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteTargetId && handleDelete(deleteTargetId)}
              className="bg-red-600 text-destructive-foreground hover:bg-destructive/90"
            >
              <span className="text-white">削除</span>
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
