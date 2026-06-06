import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
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

  it("renders prose without introducing any button", () => {
    render(<Markdown variant="chat">{"ただのテキストです"}</Markdown>);

    expect(screen.getByText("ただのテキストです")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
