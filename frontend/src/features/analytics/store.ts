import { createStore } from "../../lib/store";

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface AnalyticsState {}

export const useAnalyticsStore = createStore<AnalyticsState>("analytics", () => ({}));
