import { createStore } from "../lib/store";

export type AuthMethod = "telegram" | "pwa" | "web" | "none";

export interface AuthState {
  /** Telegram user ID (0 = unknown) */
  userId: number;
  /** User is approved and has full access */
  isApproved: boolean;
  /** User is waiting for admin approval */
  isPending: boolean;
  /** How the user authenticated */
  authMethod: AuthMethod;
  /** Raw Telegram initData (for PWA storage) */
  initData: string;
}

export interface AuthActions {
  /** Set user as fully authenticated and approved */
  setAuth: (userId: number, method: AuthMethod, initData: string) => void;
  /** Set user as pending admin approval */
  setPending: (userId: number, method: AuthMethod, initData: string) => void;
  /** Clear all auth state (logout) */
  clearAuth: () => void;
}

const initialState: AuthState = {
  userId: 0,
  isApproved: false,
  isPending: false,
  authMethod: "none",
  initData: "",
};

export const useAuthStore = createStore<AuthState & AuthActions>(
  "AuthStore",
  (set) => ({
    ...initialState,

    setAuth: (userId, method, initData) =>
      set({
        userId,
        isApproved: true,
        isPending: false,
        authMethod: method,
        initData,
      }),

    setPending: (userId, method, initData) =>
      set({
        userId,
        isApproved: false,
        isPending: true,
        authMethod: method,
        initData,
      }),

    clearAuth: () => set({ ...initialState }),
  }),
);
