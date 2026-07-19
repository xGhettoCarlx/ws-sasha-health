import { createStore } from "../lib/store";

interface ReminderSettings {
  enabled: boolean;
  time: string;
  days: string[];
}

interface PharmacyState {
  reminders: Record<number, ReminderSettings>;
}

interface PharmacyActions {
  setReminder: (medId: number, settings: ReminderSettings) => void;
  toggleReminder: (medId: number, enabled: boolean) => void;
}

export const usePharmacyStore = createStore<PharmacyState & PharmacyActions>(
  "PharmacyStore",
  (set) => ({
    reminders: {},

    setReminder: (medId, settings) =>
      set((state) => ({
        reminders: { ...state.reminders, [medId]: settings },
      })),

    toggleReminder: (medId, enabled) =>
      set((state) => {
        const existing = state.reminders[medId];
        if (!existing) return state;
        return {
          reminders: {
            ...state.reminders,
            [medId]: { ...existing, enabled },
          },
        };
      }),
  }),
);
