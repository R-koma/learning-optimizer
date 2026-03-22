import { headers } from "next/headers";
import { fetchAPI, getToken } from "@/lib/api";
import { NoteList } from "@/components/notes/note-list";

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

export default async function NotesPage() {
  const cookieHeader = (await headers()).get("cookie") ?? "";
  const token = await getToken(cookieHeader);
  const { notes } = await fetchAPI<{ notes: NoteResponse[] }>("/api/notes", {
    token,
  });

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="mb-6 text-2xl font-bold">学習履歴</h1>
      <NoteList notes={notes} />
    </div>
  );
}
