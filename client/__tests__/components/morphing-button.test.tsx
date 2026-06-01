import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MorphingButton } from "@/components/auth/morphing-button";

describe("MorphingButton", () => {
  it("is enabled when neither loading nor disabled", () => {
    render(<MorphingButton isLoading={false}>続ける</MorphingButton>);
    expect(screen.getByRole("button")).toBeEnabled();
  });

  it("is disabled while loading", () => {
    render(<MorphingButton isLoading={true}>続ける</MorphingButton>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("respects an external disabled prop without it being overridden", () => {
    render(
      <MorphingButton isLoading={false} disabled>
        続ける
      </MorphingButton>,
    );
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
