import { describe, it, expect } from "vitest";
import { getCategoryOptions, UNCATEGORIZED_LABEL } from "@/lib/note-grouping";

interface TestNote {
  id: string;
  category?: string | null;
}

describe("getCategoryOptions", () => {
  it("returns distinct categories preserving first-seen order", () => {
    const notes: TestNote[] = [
      { id: "1", category: "数学" },
      { id: "2", category: "英語" },
      { id: "3", category: "数学" },
    ];

    expect(getCategoryOptions(notes)).toEqual(["数学", "英語"]);
  });

  it("appends the uncategorized label last when null/empty categories exist", () => {
    const notes: TestNote[] = [
      { id: "1", category: null },
      { id: "2", category: "数学" },
      { id: "3", category: "  " },
      { id: "4" },
    ];

    expect(getCategoryOptions(notes)).toEqual(["数学", UNCATEGORIZED_LABEL]);
  });

  it("omits the uncategorized label when every note has a category", () => {
    const notes: TestNote[] = [
      { id: "1", category: "数学" },
      { id: "2", category: "英語" },
    ];

    expect(getCategoryOptions(notes)).toEqual(["数学", "英語"]);
  });

  it("trims surrounding whitespace and treats them as the same category", () => {
    const notes: TestNote[] = [
      { id: "1", category: "数学" },
      { id: "2", category: " 数学 " },
    ];

    expect(getCategoryOptions(notes)).toEqual(["数学"]);
  });

  it("returns an empty array for no notes", () => {
    expect(getCategoryOptions([])).toEqual([]);
  });
});
