import { describe, it, expect } from "vitest";
import { closeOpenCodeFence } from "@/lib/chat-markdown";

describe("closeOpenCodeFence", () => {
  it("appends a closing fence when a code block is left open", () => {
    const streaming = "説明します\n```python\nprint('hi')";
    expect(closeOpenCodeFence(streaming)).toBe(
      "説明します\n```python\nprint('hi')\n```",
    );
  });

  it("leaves content untouched when fences are balanced", () => {
    const closed = "```python\nprint('hi')\n```";
    expect(closeOpenCodeFence(closed)).toBe(closed);
  });

  it("leaves plain text without fences untouched", () => {
    const text = "コードはまだありません";
    expect(closeOpenCodeFence(text)).toBe(text);
  });

  it("only counts fences at the start of a line", () => {
    const inline = "これは ```inline``` ではない";
    expect(closeOpenCodeFence(inline)).toBe(inline);
  });
});
