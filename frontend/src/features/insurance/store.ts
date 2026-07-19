import { createStore } from "../../lib/store";

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface InsuranceState {}

export const useInsuranceStore = createStore<InsuranceState>("insurance", () => ({}));
