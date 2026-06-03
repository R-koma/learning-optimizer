import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import MainError from "@/app/(main)/error";

describe("(main)/error.tsx", () => {
  it("renders a user-facing error message", () => {
    render(<MainError error={new Error("boom")} reset={vi.fn()} />);
    expect(screen.getByText("問題が発生しました")).toBeInTheDocument();
  });

  it("does not leak the raw error message to the UI", () => {
    render(
      <MainError error={new Error("internal-stack-trace")} reset={vi.fn()} />,
    );
    expect(screen.queryByText(/internal-stack-trace/)).toBeNull();
  });

  it("calls reset when the retry button is clicked", () => {
    const reset = vi.fn();
    render(<MainError error={new Error("boom")} reset={reset} />);
    fireEvent.click(screen.getByRole("button", { name: "再試行" }));
    expect(reset).toHaveBeenCalledOnce();
  });
});
