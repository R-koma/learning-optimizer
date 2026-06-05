import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Markdown } from "@/components/ui/markdown";

const codeMessage = ["```python", 'print("hello")', "```"].join("\n");

describe("Markdown (chat variant)", () => {
  it("renders fenced code as a highlighted code block", () => {
    const { container } = render(
      <Markdown variant="chat">{codeMessage}</Markdown>,
    );

    const code = container.querySelector("pre code");
    expect(code).not.toBeNull();
    expect(code?.className).toContain("language-python");
    expect(container.querySelector("pre")?.textContent).toContain(
      'print("hello")',
    );
  });

  it("shows a copy button that writes the code to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });

    render(<Markdown variant="chat">{codeMessage}</Markdown>);

    await userEvent.click(
      screen.getByRole("button", { name: "コードをコピー" }),
    );

    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    expect(writeText.mock.calls[0][0]).toContain('print("hello")');
  });

  it("renders prose without a copy button", () => {
    render(<Markdown variant="chat">{"ただのテキストです"}</Markdown>);

    expect(screen.getByText("ただのテキストです")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
