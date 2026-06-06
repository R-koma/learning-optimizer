import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MessageCopyButton } from "@/components/chat/message-copy-button";

const message = ["コードはこちらです", "```python", 'print("hi")', "```"].join(
  "\n",
);

describe("MessageCopyButton", () => {
  it("copies the entire message (prose and code) to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });

    render(<MessageCopyButton content={message} />);
    await userEvent.click(
      screen.getByRole("button", { name: "メッセージをコピー" }),
    );

    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    expect(writeText.mock.calls[0][0]).toBe(message);
  });
});
