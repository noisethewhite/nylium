import type { ObjectView, PropValue, TypeView } from "../contracts";
import { TypeNames } from "../contracts";
import { NyliumApi } from "../net/nylium-api";
import { HttpError } from "../net/http-transport";
import { Observable } from "./observable";

/** VS Code-style tabs: recently opened types/objects, plus the
 * transient create-type form. */
export type Tab =
  | { readonly kind: "type"; readonly name: string }
  | { readonly kind: "object"; readonly uuid: string }
  | { readonly kind: "create-type" };

export interface WorkspaceState {
  readonly loading: boolean;
  readonly types: readonly TypeView[];
  readonly objects: readonly ObjectView[];
  readonly tabs: readonly Tab[];
  readonly activeTab: Tab | null;
  readonly error: string | null;
}

const INITIAL_STATE: WorkspaceState = {
  loading: true,
  types: [],
  objects: [],
  tabs: [],
  activeTab: null,
  error: null,
};

export function sameTab(a: Tab, b: Tab): boolean {
  if (a.kind !== b.kind) {
    return false;
  }
  if (a.kind === "type" && b.kind === "type") {
    return a.name === b.name;
  }
  if (a.kind === "object" && b.kind === "object") {
    return a.uuid === b.uuid;
  }
  return true; // single create-type tab
}

/** The screen's source of truth: open tabs, every type, every object.
 * All server traffic funnels through here — components only call
 * actions. */
export class WorkspaceStore extends Observable<WorkspaceState> {
  private readonly api: NyliumApi;
  private readonly onUnauthorized: () => void;

  constructor(api: NyliumApi, onUnauthorized: () => void) {
    super(INITIAL_STATE);
    this.api = api;
    this.onUnauthorized = onUnauthorized;
  }

  async init(): Promise<void> {
    await this.guard(async () => {
      const types = await this.api.listTypes();
      this.setState({ ...this.getSnapshot(), types });
      for (const view of this.userTypes()) {
        await this.refreshObjectsOf(view.name);
      }
      this.setState({ ...this.getSnapshot(), loading: false });
    });
  }

  openType(name: string): void {
    this.activate({ kind: "type", name });
  }

  openObject(uuid: string): void {
    this.activate({ kind: "object", uuid });
  }

  openCreateType(): void {
    this.activate({ kind: "create-type" });
  }

  closeTab(tab: Tab): void {
    const state = this.getSnapshot();
    const tabs = state.tabs.filter((open) => !sameTab(open, tab));
    const activeTab =
      state.activeTab !== null && sameTab(state.activeTab, tab)
        ? (tabs[tabs.length - 1] ?? null)
        : state.activeTab;
    this.setState({ ...state, tabs, activeTab });
  }

  async createType(name: string, props: Record<string, string>): Promise<void> {
    await this.guard(async () => {
      const created = await this.api.createType(name, props);
      const state = this.getSnapshot();
      const tabs = state.tabs.filter((tab) => tab.kind !== "create-type");
      const tab: Tab = { kind: "type", name: created.name };
      this.setState({
        ...state,
        types: [...state.types, created],
        tabs: tabs.some((open) => sameTab(open, tab)) ? tabs : [...tabs, tab],
        activeTab: tab,
      });
    });
  }

  async deleteType(name: string): Promise<void> {
    await this.guard(async () => {
      await this.api.deleteType(name);
      const state = this.getSnapshot();
      const doomed = new Set(
        state.objects.filter((o) => o.type_name === name).map((o) => o.uuid),
      );
      const tabs = state.tabs.filter(
        (tab) =>
          !(tab.kind === "type" && tab.name === name) &&
          !(tab.kind === "object" && doomed.has(tab.uuid)),
      );
      const activeTab =
        state.activeTab !== null && tabs.some((tab) => sameTab(tab, state.activeTab as Tab))
          ? state.activeTab
          : (tabs[tabs.length - 1] ?? null);
      this.setState({
        ...state,
        types: state.types.filter((view) => view.name !== name),
        objects: state.objects.filter((o) => o.type_name !== name),
        tabs,
        activeTab,
      });
    });
  }

  async createObject(typeName: string): Promise<void> {
    await this.guard(async () => {
      const created = await this.api.createObject(typeName, {});
      this.setState({
        ...this.getSnapshot(),
        objects: [...this.getSnapshot().objects, created],
      });
      this.openObject(created.uuid);
    });
  }

  async deleteObject(uuid: string): Promise<void> {
    await this.guard(async () => {
      await this.api.deleteObject(uuid);
      this.setState({
        ...this.getSnapshot(),
        objects: this.getSnapshot().objects.filter((o) => o.uuid !== uuid),
      });
      this.closeTab({ kind: "object", uuid });
    });
  }

  /** The editor's save path — writes through, then patches the list. */
  async saveObject(uuid: string, props: Record<string, PropValue>): Promise<ObjectView> {
    const updated = await this.api.updateObject(uuid, props);
    this.setState({
      ...this.getSnapshot(),
      objects: this.getSnapshot().objects.map((o) => (o.uuid === uuid ? updated : o)),
    });
    return updated;
  }

  userTypes(): readonly TypeView[] {
    return this.getSnapshot().types.filter((view) => TypeNames.isUserType(view.name));
  }

  /** Read-through for the editor's ref pickers — components never
   * touch the transport directly. */
  listObjectsOfType(typeName: string): Promise<ObjectView[]> {
    return this.api.listObjects(typeName);
  }

  private activate(tab: Tab): void {
    const state = this.getSnapshot();
    const tabs = state.tabs.some((open) => sameTab(open, tab))
      ? state.tabs
      : [...state.tabs, tab];
    this.setState({ ...state, tabs, activeTab: tab });
  }

  private async refreshObjectsOf(typeName: string): Promise<void> {
    const fresh = await this.api.listObjects(typeName);
    const rest = this.getSnapshot().objects.filter((o) => o.type_name !== typeName);
    this.setState({ ...this.getSnapshot(), objects: [...rest, ...fresh] });
  }

  private async guard(action: () => Promise<void>): Promise<void> {
    try {
      await action();
      this.setState({ ...this.getSnapshot(), error: null });
    } catch (caught: unknown) {
      if (caught instanceof HttpError && caught.status === 401) {
        // session expired mid-flight — the auth store flips the screen
        this.onUnauthorized();
        return;
      }
      const message = caught instanceof Error ? caught.message : String(caught);
      this.setState({ ...this.getSnapshot(), error: message });
    }
  }
}
