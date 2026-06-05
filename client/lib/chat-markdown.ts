const FENCE_LINE = /^```/gm;

/**
 * ストリーミング中の未閉じコードフェンスを閉じる。
 *
 * LLM 応答は 1 文字ずつ届くため、``` 開始だけ到着して閉じ ``` が未着の状態が必ず発生する。
 * このとき Markdown はフェンス以降を生テキストとして描画してしまい表示が崩れるため、
 * フェンス数が奇数なら一時的に閉じフェンスを補い、コードブロックとして描画させる。
 */
export function closeOpenCodeFence(content: string): string {
  const fenceCount = content.match(FENCE_LINE)?.length ?? 0;
  if (fenceCount % 2 === 1) {
    return `${content}\n\`\`\``;
  }
  return content;
}
