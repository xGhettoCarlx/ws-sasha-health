import { createStore } from "../../lib/store";

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface HistoryState {}

export const useHistoryStore = createStore<HistoryState>("history", () => ({}));
