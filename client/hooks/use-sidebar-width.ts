import { useState, useSyncExternalStore } from "react";

export const SIDEBAR_MIN_WIDTH = 200;
export const SIDEBAR_MAX_WIDTH = 480;
export const SIDEBAR_DEFAULT_WIDTH = 256;

const STORAGE_KEY = "sidebar-width";

export function clampWidth(width: number): number {
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, width));
}

const listeners = new Set<() => void>();

function readStored(): number {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw === null) return SIDEBAR_DEFAULT_WIDTH;
  const parsed = Number(raw);
  return Number.isNaN(parsed) ? SIDEBAR_DEFAULT_WIDTH : clampWidth(parsed);
}

function persistWidth(width: number): void {
  window.localStorage.setItem(STORAGE_KEY, String(clampWidth(width)));
  // 同一タブ内の購読者へ通知（storage イベントは他タブにしか飛ばない）
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const onStorage = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) listener();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

interface UseSidebarWidth {
  width: number;
  isResizing: boolean;
  startResize: (e: React.MouseEvent) => void;
}

/**
 * サイドバーの幅をドラッグで調整し、localStorage に永続化する。
 * 保存値は useSyncExternalStore 経由で読むため、SSR は既定幅・クライアントは保存値という
 * 二段階描画になりハイドレーション不整合を避けられる（[[use-hydrated]] と同じ手法）。
 */
export function useSidebarWidth(): UseSidebarWidth {
  const persisted = useSyncExternalStore(
    subscribe,
    readStored,
    () => SIDEBAR_DEFAULT_WIDTH,
  );
  // ドラッグ中のみ一時的に上書きする幅。null のときは永続値をそのまま使う
  const [dragWidth, setDragWidth] = useState<number | null>(null);

  const width = dragWidth ?? persisted;

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = persisted;
    let current = startWidth;
    setDragWidth(startWidth);

    // ドラッグ中はテキスト選択とカーソルのちらつきを抑止する
    const previousUserSelect = document.body.style.userSelect;
    const previousCursor = document.body.style.cursor;
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";

    const onMove = (ev: MouseEvent) => {
      current = clampWidth(startWidth + ev.clientX - startX);
      setDragWidth(current);
    };
    const onUp = () => {
      document.body.style.userSelect = previousUserSelect;
      document.body.style.cursor = previousCursor;
      persistWidth(current);
      setDragWidth(null);
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };

  return { width, isResizing: dragWidth !== null, startResize };
}
