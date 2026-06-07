import { describe, it, expect } from "vitest";
import {
  buildCalendarGrid,
  buildCalendarWeeks,
  startOfMonth,
  addMonths,
  isSameDay,
} from "@/lib/calendar-grid";
import { toLocalDateKey } from "@/lib/group-notes-by-date";

describe("buildCalendarGrid", () => {
  it("always returns 42 cells (6 weeks)", () => {
    expect(buildCalendarGrid(new Date(2026, 5, 1))).toHaveLength(42);
  });

  it("starts on the Sunday on or before the first of the month", () => {
    // 2026-06-01 は月曜。前日の日曜 2026-05-31 から始まる
    const grid = buildCalendarGrid(new Date(2026, 5, 1));
    expect(grid[0].date.getDay()).toBe(0);
    expect(toLocalDateKey(grid[0].date)).toBe("2026-05-31");
    expect(grid[0].inCurrentMonth).toBe(false);
  });

  it("marks days of the viewed month as inCurrentMonth", () => {
    const grid = buildCalendarGrid(new Date(2026, 5, 1));
    const first = grid.find((d) => toLocalDateKey(d.date) === "2026-06-01");
    const last = grid.find((d) => toLocalDateKey(d.date) === "2026-06-30");
    expect(first?.inCurrentMonth).toBe(true);
    expect(last?.inCurrentMonth).toBe(true);
  });
});

describe("buildCalendarWeeks", () => {
  it("returns rows of 7 days", () => {
    const weeks = buildCalendarWeeks(new Date(2026, 5, 1));
    expect(weeks.every((week) => week.length === 7)).toBe(true);
  });

  it("keeps every week that contains a day of the viewed month", () => {
    const weeks = buildCalendarWeeks(new Date(2026, 5, 1));
    expect(weeks.every((week) => week.some((d) => d.inCurrentMonth))).toBe(
      true,
    );
  });

  it("drops trailing weeks that belong entirely to another month", () => {
    // 2026年2月は日曜始まり・28日なので、ちょうど4週に収まり余分な週は出ない
    const weeks = buildCalendarWeeks(new Date(2026, 1, 1));
    expect(weeks).toHaveLength(4);
  });
});

describe("startOfMonth / addMonths", () => {
  it("returns the first day of the month", () => {
    expect(toLocalDateKey(startOfMonth(new Date(2026, 5, 17)))).toBe(
      "2026-06-01",
    );
  });

  it("shifts months and wraps the year", () => {
    expect(toLocalDateKey(addMonths(new Date(2026, 11, 1), 1))).toBe(
      "2027-01-01",
    );
    expect(toLocalDateKey(addMonths(new Date(2026, 0, 1), -1))).toBe(
      "2025-12-01",
    );
  });
});

describe("isSameDay", () => {
  it("compares calendar day ignoring time", () => {
    expect(isSameDay(new Date(2026, 5, 1, 9), new Date(2026, 5, 1, 23))).toBe(
      true,
    );
    expect(isSameDay(new Date(2026, 5, 1), new Date(2026, 5, 2))).toBe(false);
  });
});
