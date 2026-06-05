import { describe, it, expect } from "vitest";
import { buildNoteMarkdown } from "@/lib/note-markdown";

describe("buildNoteMarkdown", () => {
  it("includes topic as an H1 heading", () => {
    const md = buildNoteMarkdown({
      topic: "React の状態管理",
      summary: "要約テキスト",
      content: "本文テキスト",
    });
    expect(md).toContain("# React の状態管理");
  });

  it("includes summary and content under labeled sections", () => {
    const md = buildNoteMarkdown({
      topic: "トピック",
      summary: "これは要約です",
      content: "これは本文です",
    });
    expect(md).toContain("## 要約\n\nこれは要約です");
    expect(md).toContain("## 内容\n\nこれは本文です");
  });

  it("omits the summary section when summary is empty", () => {
    const md = buildNoteMarkdown({
      topic: "トピック",
      summary: "   ",
      content: "本文",
    });
    expect(md).not.toContain("## 要約");
    expect(md).toContain("## 内容");
  });

  it("trims surrounding whitespace from fields", () => {
    const md = buildNoteMarkdown({
      topic: "  トピック  ",
      summary: "  要約  ",
      content: "  本文  ",
    });
    expect(md).toContain("# トピック\n");
    expect(md).toContain("要約\n");
    expect(md).not.toContain("  トピック");
  });

  it("ends with a single trailing newline", () => {
    const md = buildNoteMarkdown({
      topic: "トピック",
      summary: "要約",
      content: "本文",
    });
    expect(md.endsWith("\n")).toBe(true);
    expect(md.endsWith("\n\n")).toBe(false);
  });
});
