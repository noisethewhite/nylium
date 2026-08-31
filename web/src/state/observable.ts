/** Observable store base — the behavior every store shares.
 * Bound to React through useSyncExternalStore via useObservable. */

export type Listener = () => void;

export abstract class Observable<TState> {
  private state: TState;
  private readonly listeners = new Set<Listener>();

  protected constructor(initial: TState) {
    this.state = initial;
  }

  readonly subscribe = (listener: Listener): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  readonly getSnapshot = (): TState => this.state;

  protected setState(next: TState): void {
    this.state = next;
    for (const listener of this.listeners) {
      listener();
    }
  }
}
