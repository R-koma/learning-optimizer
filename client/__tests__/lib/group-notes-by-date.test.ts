import { describe, it, expect } from "vitest";
import { groupNotesByDate, toLocalDateKey } from "@/lib/group-notes-by-date";

interface TestNote {
  id: string;
  created_at: string;
}

describe("toLocalDateKey", () => {
  it("formats a date as zero-padded YYYY-MM-DD in local time", () => {
    const date = new Date(2026, 0, 5); // 2026-01-05 ローカル
    expect(toLocalDateKey(date)).toBe("2026-01-05");
  });
});

describe("groupNotesByDate", () => {
  it("groups notes sharing a local day and preserves input order", () => {
    // ローカル正午ちょうどなら実行環境の TZ に関わらず暦日が揺れない
    const notes: TestNote[] = [
      { id: "1", created_at: new Date(2026, 5, 1, 12).toISOString() },
      { id: "2", created_at: new Date(2026, 5, 2, 12).toISOString() },
      { id: "3", created_at: new Date(2026, 5, 1, 12).toISOString() },
    ];

    const grouped = groupNotesByDate(notes);

    expect(grouped.get("2026-06-01")).toEqual([notes[0], notes[2]]);
    expect(grouped.get("2026-06-02")).toEqual([notes[1]]);
  });

  it("returns an empty map for no notes", () => {
    expect(groupNotesByDate([]).size).toBe(0);
  });

  it("buckets by local calendar day, not UTC day", () => {
    // ローカル日付に変換した上で同じ日に入ることを、変換結果同士で突き合わせて検証する
    const a = { id: "a", created_at: "2026-06-10T00:30:00Z" };
    const b = { id: "b", created_at: "2026-06-10T15:30:00Z" };
    const grouped = groupNotesByDate([a, b]);

    const keyA = toLocalDateKey(new Date(a.created_at));
    const keyB = toLocalDateKey(new Date(b.created_at));
    if (keyA === keyB) {
      expect(grouped.get(keyA)).toEqual([a, b]);
    } else {
      expect(grouped.get(keyA)).toEqual([a]);
      expect(grouped.get(keyB)).toEqual([b]);
    }
  });
});
