import { createStore } from "../lib/store";

interface DashboardState {
  lastBp: string;
  lastPulse: number;
  selectedQuickAction: string | null;
}

interface DashboardActions {
  setLastBp: (bp: string) => void;
  setLastPulse: (pulse: number) => void;
  setSelectedQuickAction: (action: string | null) => void;
}

export const useDashboardStore = createStore<DashboardState & DashboardActions>(
  "DashboardStore",
  (set) => ({
    lastBp: "",
    lastPulse: 0,
    selectedQuickAction: null,

    setLastBp: (bp) => set({ lastBp: bp }),
    setLastPulse: (pulse) => set({ lastPulse: pulse }),
    setSelectedQuickAction: (action) => set({ selectedQuickAction: action }),
  }),
);
