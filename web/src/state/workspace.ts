import type { ObjectView, PropValue, TypeView } from "../contracts";
import { TypeNames } from "../contracts";
import { NyliumApi } from "../net/nylium-api";
import { HttpError } from "../net/http-transport";
import { Observable } from "./observable";

/** VS Code-style tabs: recently opened types/objects, plus the
 * transient create-type / create-enum forms. */
export type Tab =
  | { readonly kind: "type"; readonly name: string }
  | { readonly kind: "object"; readonly uuid: string }
  | { readonly kind: "create-type" }
  | { readonly kind: "create-enum" };

export interface WorkspaceState {
  readonly loading: boolean;
  readonly types: readonly TypeView[];
  readonly objects: readonly ObjectView[];
  readonly tabs: readonly Tab[];
  readonly activeTab: Tab | null;
}

const INITIAL_STATE: WorkspaceState = {
  loading: true,
  types: [],
  objects: [],
  tabs: [],
  activeTab: null,
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
  return true; // one tab per create-* form kind
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

  openCreateEnum(): void {
    this.activate({ kind: "create-enum" });
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

  async createType(
    name: string,
    pluralName: string,
    props: Record<string, string>,
    icon?: string,
    color?: string,
  ): Promise<void> {
    await this.guard(async () => {
      const created = await this.api.createType(name, pluralName, props, icon, color);
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

  async createEnum(name: string, options: string[]): Promise<void> {
    await this.guard(async () => {
      const created = await this.api.createEnum(name, options);
      const state = this.getSnapshot();
      const tabs = state.tabs.filter((tab) => tab.kind !== "create-enum");
      const tab: Tab = { kind: "type", name: created.name };
      this.setState({
        ...state,
        types: [...state.types, created],
        tabs: tabs.some((open) => sameTab(open, tab)) ? tabs : [...tabs, tab],
        activeTab: tab,
      });
    });
  }

  /** The enum page's save: meta patch first (rename must precede the
   * options PUT), then the full option draft. Renames propagate into
   * stored values server-side, so every type's objects get re-pulled. */
  async saveEnumEdits(
    typeName: string,
    patch: { name: string; icon: string; color: string },
    options: { uuid: string | null; value: string }[],
  ): Promise<void> {
    await this.guard(async () => {
      const current = this.getSnapshot().types.find((v) => v.name === typeName);
      if (!current) {
        return;
      }
      let schema = current;
      const metaChanged =
        patch.name !== current.name ||
        patch.icon !== current.icon ||
        patch.color !== current.color;
      if (metaChanged) {
        const rename: { name?: string; icon?: string; color?: string } = {};
        if (patch.name !== current.name) {
          rename.name = patch.name;
        }
        if (patch.icon !== current.icon) {
          rename.icon = patch.icon;
        }
        if (patch.color !== current.color) {
          rename.color = patch.color;
        }
        schema = await this.api.updateType(typeName, rename);
      }
      schema = await this.api.syncEnumOptions(schema.name, options);
      const state = this.getSnapshot();
      const renamed = schema.name !== typeName;
      const tabs = state.tabs.map((tab) =>
        renamed && tab.kind === "type" && tab.name === typeName
          ? { kind: "type" as const, name: schema.name }
          : tab,
      );
      const activeTab =
        renamed && state.activeTab?.kind === "type" && state.activeTab.name === typeName
          ? { kind: "type" as const, name: schema.name }
          : state.activeTab;
      this.setState({
        ...state,
        types: state.types.map((view) => (view.name === typeName ? schema : view)),
        tabs,
        activeTab,
      });
      // option renames rewrote stored values across every user type
      for (const view of this.userTypes()) {
        await this.refreshObjectsOf(view.name);
      }
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

  /** Drag-and-drop reorder in the type view — the server answers with
   * the re-sorted schema, which we swap into the type list. */
  async reorderProps(typeName: string, keys: string[]): Promise<void> {
    await this.guard(async () => {
      const updated = await this.api.reorderProps(typeName, keys);
      this.setState({
        ...this.getSnapshot(),
        types: this.getSnapshot().types.map((view) =>
          view.name === typeName ? updated : view,
        ),
      });
    });
  }

  /** The type editor's save path: rename first (the schema PUT needs the
   * final name), then the full prop draft, then refresh both the type
   * list and the objects whose values a retype/delete may have wiped. */
  async saveTypeEdits(
    typeName: string,
    patch: { name: string; plural_name: string; icon: string; color: string },
    props: { uuid: string | null; key: string; value_type: string }[],
  ): Promise<void> {
    await this.guard(async () => {
      const current = this.getSnapshot().types.find((v) => v.name === typeName);
      if (!current) {
        return;
      }
      let schema = current;
      const metaChanged =
        patch.name !== current.name ||
        patch.plural_name !== current.plural_name ||
        patch.icon !== current.icon ||
        patch.color !== current.color;
      if (metaChanged) {
        const rename: { name?: string; plural_name?: string; icon?: string; color?: string } = {};
        if (patch.name !== current.name) {
          rename.name = patch.name;
        }
        if (patch.plural_name !== current.plural_name) {
          rename.plural_name = patch.plural_name;
        }
        if (patch.icon !== current.icon) {
          rename.icon = patch.icon;
        }
        if (patch.color !== current.color) {
          rename.color = patch.color;
        }
        schema = await this.api.updateType(typeName, rename);
      }
      schema = await this.api.syncProps(schema.name, props);
      const state = this.getSnapshot();
      const renamed = schema.name !== typeName;
      const tabs = state.tabs.map((tab) =>
        renamed && tab.kind === "type" && tab.name === typeName
          ? { kind: "type" as const, name: schema.name }
          : tab,
      );
      const activeTab =
        renamed && state.activeTab?.kind === "type" && state.activeTab.name === typeName
          ? { kind: "type" as const, name: schema.name }
          : state.activeTab;
      this.setState({
        ...state,
        types: state.types.map((view) => (view.name === typeName ? schema : view)),
        tabs,
        activeTab,
      });
      // values may have been purged by a retype/delete — re-pull objects
      await this.refreshObjectsOf(schema.name);
      if (renamed) {
        // objects now carry the new type name — drop the stale ones
        const fresh = this.getSnapshot().objects.filter(
          (o) => !(o.type_name === typeName),
        );
        this.setState({ ...this.getSnapshot(), objects: fresh });
        await this.refreshObjectsOf(schema.name);
      }
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

  /** Any type by name, builtins included — pickers render their icons. */
  typeView(name: string): TypeView | undefined {
    return this.getSnapshot().types.find((view) => view.name === name);
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
    } catch (caught: unknown) {
      if (caught instanceof HttpError && caught.status === 401) {
        // session expired mid-flight — the auth store flips the screen
        this.onUnauthorized();
        return;
      }
      // transport already reported the failure to the error log —
      // the workspace only stops the action here
    }
  }
}
