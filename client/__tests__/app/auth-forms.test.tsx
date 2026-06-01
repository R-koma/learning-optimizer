import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/auth-client", () => ({
  authClient: {
    signIn: { email: vi.fn(), social: vi.fn() },
    signUp: { email: vi.fn() },
  },
}));

import SignInPage from "@/app/(auth)/sign-in/page";
import SignUpPage from "@/app/(auth)/sign-up/page";

describe("auth forms guard against native GET credential leaks", () => {
  it("sign-in form uses method=post", () => {
    const { container } = render(<SignInPage />);
    const form = container.querySelector("#sign-in-form");
    expect(form).not.toBeNull();
    expect(form?.getAttribute("method")).toBe("post");
  });

  it("sign-up form uses method=post", () => {
    const { container } = render(<SignUpPage />);
    const form = container.querySelector("#sign-up-form");
    expect(form).not.toBeNull();
    expect(form?.getAttribute("method")).toBe("post");
  });
});
