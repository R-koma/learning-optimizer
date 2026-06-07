import { headers } from "next/headers";
import { fetchAPI, getToken } from "@/lib/api";
import { NoteList } from "@/components/notes/note-list";

interface NoteResponse {
  id: string;
  topic: string;
  content: string;
  summary: string | null;
  status: string;
  category: string | null;
  created_at: string;
  updated_at: string;
  review_count: number;
}

export default async function NotesPage() {
  const cookieHeader = (await headers()).get("cookie") ?? "";
  const token = await getToken(cookieHeader);
  const { notes } = await fetchAPI<{ notes: NoteResponse[] }>("/api/notes", {
    token,
  });

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="mb-6 border-l-4 border-muted-foreground/40 pl-4">
        <p className="mb-1 text-xs font-semibold tracking-widest text-muted-foreground">
          HISTORY
        </p>
        <h1 className="text-2xl font-bold">学習履歴</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {notes.length > 0
            ? `${notes.length} 件のノートが保存されています`
            : "まだノートがありません"}
        </p>
      </div>
      <NoteList notes={notes} />
    </div>
  );
}
