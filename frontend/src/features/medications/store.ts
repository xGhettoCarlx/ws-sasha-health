import { createStore } from "../../lib/store";

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface MedicationsState {}

export const useMedicationsStore = createStore<MedicationsState>("medications", () => ({}));
