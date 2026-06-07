export interface CalendarDay {
  date: Date;
  inCurrentMonth: boolean;
}

const DAYS_IN_GRID = 42; // 常に6週ぶん描画し、月をまたいでも高さを一定に保つ

/**
 * 指定月のカレンダーグリッド（日曜始まり・6週=42マス）を返す。前後の月にはみ出すマスは
 * `inCurrentMonth: false` を立てる。月の高さを固定するため常に 42 マス返す。
 */
export function buildCalendarGrid(viewDate: Date): CalendarDay[] {
  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();
  const startWeekday = new Date(year, month, 1).getDay(); // 0=日曜

  const days: CalendarDay[] = [];
  for (let i = 0; i < DAYS_IN_GRID; i++) {
    const date = new Date(year, month, 1 - startWeekday + i);
    days.push({ date, inCurrentMonth: date.getMonth() === month });
  }
  return days;
}

/**
 * 指定月のカレンダーを「週（7マス）の配列」で返す。当月の日を1つも含まない週（末尾に出る
 * 翌月だけの週など）は除外する。これにより月に無関係な週を表示せずに済む。各週には前後の月の
 * マス（`inCurrentMonth: false`）が残るので、描画側で空セルにするかどうかを決められる。
 */
export function buildCalendarWeeks(viewDate: Date): CalendarDay[][] {
  const days = buildCalendarGrid(viewDate);
  const weeks: CalendarDay[][] = [];
  for (let i = 0; i < days.length; i += 7) {
    weeks.push(days.slice(i, i + 7));
  }
  return weeks.filter((week) => week.some((day) => day.inCurrentMonth));
}

export function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

export function addMonths(date: Date, delta: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + delta, 1);
}

export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}
