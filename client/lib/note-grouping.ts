export const UNCATEGORIZED_LABEL = "未分類";

/**
 * ノートから重複なしのカテゴリー一覧を、最初に現れた順で返す。カテゴリー未設定
 * （null / 空文字）のノートが 1 件でもあれば、末尾に「未分類」を付与する。
 * カテゴリー Select の選択肢として使う。
 */
export function getCategoryOptions(
  notes: readonly { category?: string | null }[],
): string[] {
  const categories = new Set<string>();
  let hasUncategorized = false;

  for (const note of notes) {
    const category = note.category?.trim();
    if (category) {
      categories.add(category);
    } else {
      hasUncategorized = true;
    }
  }

  const result = [...categories];
  if (hasUncategorized) {
    result.push(UNCATEGORIZED_LABEL);
  }

  return result;
}
