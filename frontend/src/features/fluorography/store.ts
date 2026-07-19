import { createStore } from "../../lib/store";

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface FluorographyState {}

export const useFluorographyStore = createStore<FluorographyState>("fluorography", () => ({}));
