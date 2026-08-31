import { useSyncExternalStore } from "react";
import type { Observable } from "./observable";

/** React boundary exception to the classes-own-behavior rule:
 * hooks must be functions named use* — this one only adapts. */
export function useObservable<TState>(store: Observable<TState>): TState {
  return useSyncExternalStore(store.subscribe, store.getSnapshot);
}
