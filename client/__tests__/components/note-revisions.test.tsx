import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NoteRevisions } from "@/components/notes/note-revisions";

describe("NoteRevisions", () => {
  it("renders nothing when there are no revisions", () => {
    const { container } = render(<NoteRevisions revisions={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders each revision with its date and content", () => {
    render(
      <NoteRevisions
        revisions={[
          {
            id: "r1",
            content: "- 計算量が O(log n) だと理解した",
            created_at: "2026-06-01T00:00:00Z",
          },
          {
            id: "r2",
            content: "- 再帰での実装も書けるようになった",
            created_at: "2026-06-05T00:00:00Z",
          },
        ]}
      />,
    );

    expect(screen.getByText("復習で深まった点")).toBeInTheDocument();
    expect(
      screen.getByText("計算量が O(log n) だと理解した"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("再帰での実装も書けるようになった"),
    ).toBeInTheDocument();
    expect(screen.getByText("2026年6月1日 の復習")).toBeInTheDocument();
  });
});
