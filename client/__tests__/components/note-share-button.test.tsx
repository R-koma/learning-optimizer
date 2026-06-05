import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NoteShareButton } from "@/components/notes/note-share-button";

const toastSuccess = vi.fn();
const toastError = vi.fn();
vi.mock("sonner", () => ({
  toast: {
    success: (msg: string) => toastSuccess(msg),
    error: (msg: string) => toastError(msg),
  },
}));

const noteProps = {
  topic: "React の状態管理",
  summary: "要約テキスト",
  content: "本文テキスト",
};

beforeEach(() => {
  toastSuccess.mockReset();
  toastError.mockReset();
});

describe("NoteShareButton", () => {
  it("writes the note as markdown to the clipboard on click", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    render(<NoteShareButton {...noteProps} />);

    await userEvent.click(screen.getByRole("button"));

    expect(writeText).toHaveBeenCalledOnce();
    const copied = writeText.mock.calls[0][0] as string;
    expect(copied).toContain("# React の状態管理");
    expect(copied).toContain("## 要約");
    expect(copied).toContain("本文テキスト");
  });

  it("shows a success toast after copying", async () => {
    vi.stubGlobal("navigator", {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
    render(<NoteShareButton {...noteProps} />);

    await userEvent.click(screen.getByRole("button"));

    await waitFor(() => expect(toastSuccess).toHaveBeenCalledOnce());
    expect(toastError).not.toHaveBeenCalled();
  });

  it("shows an error toast when clipboard write fails", async () => {
    vi.stubGlobal("navigator", {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
    });
    render(<NoteShareButton {...noteProps} />);

    await userEvent.click(screen.getByRole("button"));

    await waitFor(() => expect(toastError).toHaveBeenCalledOnce());
    expect(toastSuccess).not.toHaveBeenCalled();
  });
});
