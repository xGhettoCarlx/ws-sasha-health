import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

interface ProfileEditsState {
  /** User-edited weight value (number only, e.g. "75") — persisted to localStorage */
  editedWeight: string | null;
  /** User-edited height value (number only, e.g. "180") — persisted to localStorage */
  editedHeight: string | null;
  /** User-edited age value (number only, e.g. "35") — persisted to localStorage */
  editedAge: string | null;
  setWeight: (val: string | null) => void;
  setHeight: (val: string | null) => void;
  setAge: (val: string | null) => void;
}

export const useProfileEditsStore = create<ProfileEditsState>()(
  devtools(
    persist(
      (set) => ({
        editedWeight: null,
        editedHeight: null,
        editedAge: null,
        setWeight: (val) => set({ editedWeight: val }),
        setHeight: (val) => set({ editedHeight: val }),
        setAge: (val) => set({ editedAge: val }),
      }),
      { name: "profile-edits" },
    ),
    { name: "ProfileEditsStore" },
  ),
);
