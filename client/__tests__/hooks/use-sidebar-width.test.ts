import { describe, it, expect, beforeEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { fireEvent } from "@testing-library/react";
import {
  clampWidth,
  useSidebarWidth,
  SIDEBAR_DEFAULT_WIDTH,
  SIDEBAR_MIN_WIDTH,
  SIDEBAR_MAX_WIDTH,
} from "@/hooks/use-sidebar-width";

describe("clampWidth", () => {
  it("keeps a width within range untouched", () => {
    expect(clampWidth(300)).toBe(300);
  });

  it("clamps below the minimum and above the maximum", () => {
    expect(clampWidth(50)).toBe(SIDEBAR_MIN_WIDTH);
    expect(clampWidth(9999)).toBe(SIDEBAR_MAX_WIDTH);
  });
});

describe("useSidebarWidth", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("starts at the default width", () => {
    const { result } = renderHook(() => useSidebarWidth());
    expect(result.current.width).toBe(SIDEBAR_DEFAULT_WIDTH);
  });

  it("updates width while dragging and persists it on release", () => {
    const { result } = renderHook(() => useSidebarWidth());

    act(() => {
      result.current.startResize({
        clientX: 256,
        preventDefault: () => {},
      } as unknown as React.MouseEvent);
    });
    expect(result.current.isResizing).toBe(true);

    act(() => {
      fireEvent.mouseMove(document, { clientX: 356 });
    });
    expect(result.current.width).toBe(356);

    act(() => {
      fireEvent.mouseUp(document);
    });
    expect(result.current.isResizing).toBe(false);
    expect(window.localStorage.getItem("sidebar-width")).toBe("356");
  });

  it("restores a clamped width from localStorage on mount", () => {
    window.localStorage.setItem("sidebar-width", "9999");
    const { result } = renderHook(() => useSidebarWidth());
    expect(result.current.width).toBe(SIDEBAR_MAX_WIDTH);
  });
});
