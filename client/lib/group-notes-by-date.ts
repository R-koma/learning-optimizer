/**
 * ローカルタイムゾーンでの `YYYY-MM-DD` キーを返す。`created_at` は UTC の ISO 文字列で
 * 届くため、カレンダー上の「学習した日」をユーザーの暦に合わせるにはローカル日付へ
 * 変換する必要がある（学習履歴ページの表示と暦をそろえる）。
 */
export function toLocalDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * ノートを `created_at` のローカル日付（`YYYY-MM-DD`）単位でまとめる。各日のノートの並びは
 * 入力順を維持する。カレンダー上で「その日に学習したトピック」を引くための索引として使う。
 */
export function groupNotesByDate<T extends { created_at: string }>(
  notes: readonly T[],
): Map<string, T[]> {
  const byDate = new Map<string, T[]>();

  for (const note of notes) {
    const key = toLocalDateKey(new Date(note.created_at));
    const existing = byDate.get(key);
    if (existing) {
      existing.push(note);
    } else {
      byDate.set(key, [note]);
    }
  }

  return byDate;
}
