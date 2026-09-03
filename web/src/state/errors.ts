import { Observable } from "./observable";

export interface ErrorEntry {
  readonly id: number;
  readonly message: string;
  readonly at: Date;
}

export interface ErrorCenterState {
  /** Every error ever reported this session — the log. */
  readonly entries: readonly ErrorEntry[];
  /** Entry ids currently floating as toasts (subset of the log). */
  readonly toasts: readonly number[];
  readonly panelOpen: boolean;
}

const INITIAL_STATE: ErrorCenterState = {
  entries: [],
  toasts: [],
  panelOpen: false,
};

/** The app's error center: a persistent log behind everything, plus a
 * transient toast layer on top. Toasts never remove log entries. */
export class ErrorStore extends Observable<ErrorCenterState> {
  private nextId = 1;

  constructor() {
    super(INITIAL_STATE);
  }

  report(message: string): void {
    const entry: ErrorEntry = { id: this.nextId, message, at: new Date() };
    this.nextId += 1;
    const state = this.getSnapshot();
    this.setState({
      ...state,
      entries: [...state.entries, entry],
      // an open panel is already showing the log — no toast needed
      toasts: state.panelOpen ? state.toasts : [...state.toasts, entry.id],
    });
  }

  dismissToast(id: number): void {
    const state = this.getSnapshot();
    this.setState({
      ...state,
      toasts: state.toasts.filter((toastId) => toastId !== id),
    });
  }

  togglePanel(): void {
    const state = this.getSnapshot();
    // opening the log dismisses every toast — they live on in the log
    this.setState({
      ...state,
      panelOpen: !state.panelOpen,
      toasts: state.panelOpen ? state.toasts : [],
    });
  }

  clear(): void {
    this.setState({ ...this.getSnapshot(), entries: [], toasts: [] });
  }
}
