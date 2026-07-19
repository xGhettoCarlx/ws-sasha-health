import { createStore } from "../../lib/store";

interface RecordsState {
  selectedDate: string;
}

export const useRecordsStore = createStore<RecordsState>("records", () => ({
  selectedDate: new Date().toISOString().split("T")[0] ?? "",
}));
