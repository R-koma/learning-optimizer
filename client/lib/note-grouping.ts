export const UNCATEGORIZED_LABEL = "未分類";

export interface NoteCategoryGroup<T> {
  category: string;
  notes: T[];
}

/**
 * ノートをカテゴリー単位にまとめる。`category` 未設定（null / 空文字）のノートは
 * 「未分類」グループへ集約する。グループの並びは最初に各カテゴリーが現れた順を保ち、
 * 「未分類」は常に末尾に置く。各グループ内のノートの並びは入力順を維持する。
 */
export function groupNotesByCategory<T extends { category?: string | null }>(
  notes: readonly T[],
): NoteCategoryGroup<T>[] {
  const groups = new Map<string, T[]>();

  for (const note of notes) {
    const category = note.category?.trim()
      ? note.category.trim()
      : UNCATEGORIZED_LABEL;
    const existing = groups.get(category);
    if (existing) {
      existing.push(note);
    } else {
      groups.set(category, [note]);
    }
  }

  const result: NoteCategoryGroup<T>[] = [];
  for (const [category, groupedNotes] of groups) {
    if (category === UNCATEGORIZED_LABEL) continue;
    result.push({ category, notes: groupedNotes });
  }

  const uncategorized = groups.get(UNCATEGORIZED_LABEL);
  if (uncategorized) {
    result.push({ category: UNCATEGORIZED_LABEL, notes: uncategorized });
  }

  return result;
}
