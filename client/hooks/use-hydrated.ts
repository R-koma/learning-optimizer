import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/**
 * ハイドレーション完了後に true を返す。
 * SSR・初回クライアントレンダリングでは false を返し、ハイドレーション不整合
 * （hydration mismatch）の警告を避ける。
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true, // client snapshot
    () => false, // server snapshot
  );
}
