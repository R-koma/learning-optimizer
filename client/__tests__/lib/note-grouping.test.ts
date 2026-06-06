import { describe, it, expect } from "vitest";
import { groupNotesByCategory, UNCATEGORIZED_LABEL } from "@/lib/note-grouping";

interface TestNote {
  id: string;
  category?: string | null;
}

describe("groupNotesByCategory", () => {
  it("groups notes by their category preserving first-seen order", () => {
    const notes: TestNote[] = [
      { id: "1", category: "数学" },
      { id: "2", category: "英語" },
      { id: "3", category: "数学" },
    ];

    const groups = groupNotesByCategory(notes);

    expect(groups).toEqual([
      { category: "数学", notes: [notes[0], notes[2]] },
      { category: "英語", notes: [notes[1]] },
    ]);
  });

  it("collects null/empty categories into the uncategorized group placed last", () => {
    const notes: TestNote[] = [
      { id: "1", category: null },
      { id: "2", category: "数学" },
      { id: "3", category: "  " },
      { id: "4" },
    ];

    const groups = groupNotesByCategory(notes);

    expect(groups.map((g) => g.category)).toEqual([
      "数学",
      UNCATEGORIZED_LABEL,
    ]);
    expect(groups[1].notes.map((n) => n.id)).toEqual(["1", "3", "4"]);
  });

  it("trims surrounding whitespace when grouping", () => {
    const notes: TestNote[] = [
      { id: "1", category: "数学" },
      { id: "2", category: " 数学 " },
    ];

    const groups = groupNotesByCategory(notes);

    expect(groups).toHaveLength(1);
    expect(groups[0].notes).toHaveLength(2);
  });

  it("returns an empty array for no notes", () => {
    expect(groupNotesByCategory([])).toEqual([]);
  });
});
