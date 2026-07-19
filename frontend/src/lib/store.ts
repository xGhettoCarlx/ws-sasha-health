import { create, type StateCreator } from "zustand";
import { devtools } from "zustand/middleware";

/**
 * Zustand store creator with Redux DevTools enabled.
 * Drop-in replacement for zustand's `create` — wraps every store
 * with the devtools middleware automatically.
 *
 * Usage:
 *   import { createStore } from "../lib/store";
 *   export const useMyStore = createStore<State>("StoreName", (set, get) => ({ ... }));
 */
export function createStore<T>(
  name: string,
  initializer: StateCreator<T, [], []>,
) {
  return create<T>()(devtools(initializer, { name }));
}
