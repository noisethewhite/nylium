import type {
  FileView,
  FunctionEdgeInput,
  FunctionNodeInput,
  FunctionView,
  ObjectView,
  PropValue,
  TypeView,
} from "../contracts";
import { TypeNames } from "../contracts";
import { NyliumApi } from "../net/nylium-api";
import { HttpError } from "../net/http-transport";
import { Observable } from "./observable";

/** VS Code-style tabs: recently opened types/objects/functions, plus the
 * transient create-type / create-enum / create-function forms. */
export type Tab =
  | { readonly kind: "type"; readonly name: string; readonly preview: boolean }
  | { readonly kind: "object"; readonly uuid: string; readonly preview: boolean }
  | { readonly kind: "function"; readonly uuid: string; readonly preview: boolean }
  | { readonly kind: "calendar"; readonly preview: boolean }
  | { readonly kind: "create-type"; readonly preview: boolean }
  | { readonly kind: "create-enum"; readonly preview: boolean }
  | { readonly kind: "create-unit"; readonly preview: boolean }
  | { readonly kind: "create-function"; readonly preview: boolean };

export interface WorkspaceState {
  readonly loading: boolean;
  readonly types: readonly TypeView[];
  readonly objects: readonly ObjectView[];
  readonly functions: readonly FunctionView[];
  readonly files: readonly FileView[];
  readonly tabs: readonly Tab[];
  readonly activeTab: Tab | null;
}

const INITIAL_STATE: WorkspaceState = {
  loading: true,
  types: [],
  objects: [],
  functions: [],
  files: [],
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
  if (a.kind === "function" && b.kind === "function") {
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
      const functions = await this.api.listFunctions();
      const files = await this.api.listFiles();
      this.setState({ ...this.getSnapshot(), types, functions, files });
      for (const view of this.userTypes()) {
        await this.refreshObjectsOf(view.name);
      }
      this.setState({ ...this.getSnapshot(), loading: false });
    });
  }

  openType(name: string): void {
    this.activate({ kind: "type", name, preview: true });
  }

  openObject(uuid: string): void {
    this.activate({ kind: "object", uuid, preview: true });
  }

  openCreateType(): void {
    this.activate({ kind: "create-type", preview: false });
  }

  openCreateEnum(): void {
    this.activate({ kind: "create-enum", preview: false });
  }

  openCreateUnit(): void {
    this.activate({ kind: "create-unit", preview: false });
  }

  openFunction(uuid: string): void {
    this.activate({ kind: "function", uuid, preview: true });
  }

  openCalendar(): void {
    this.activate({ kind: "calendar", preview: false });
  }

  openCreateFunction(): void {
    this.activate({ kind: "create-function", preview: false });
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
    embedded?: boolean,
  ): Promise<void> {
    await this.guard(async () => {
      const created = await this.api.createType(name, pluralName, props, icon, color, embedded);
      const state = this.getSnapshot();
      const tabs = state.tabs.filter((tab) => tab.kind !== "create-type");
      const tab: Tab = { kind: "type", name: created.name, preview: false };
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
      const tab: Tab = { kind: "type", name: created.name, preview: false };
      this.setState({
        ...state,
        types: [...state.types, created],
        tabs: tabs.some((open) => sameTab(open, tab)) ? tabs : [...tabs, tab],
        activeTab: tab,
      });
    });
  }

  async createUnit(
    name: string,
    base: string,
    secondaries: { name: string; multiplier: number; offset: number }[],
  ): Promise<void> {
    await this.guard(async () => {
      const created = await this.api.createUnit(name, base, secondaries);
      const state = this.getSnapshot();
      const tabs = state.tabs.filter((tab) => tab.kind !== "create-unit");
      const tab: Tab = { kind: "type", name: created.name, preview: false };
      this.setState({
        ...state,
        types: [...state.types, created],
        tabs: tabs.some((open) => sameTab(open, tab)) ? tabs : [...tabs, tab],
        activeTab: tab,
      });
    });
  }

  /** The unit page's save: meta patch first (rename must precede the
   * parts PUT), then the full part draft. Part renames propagate into
   * stored unit labels server-side, so every type's objects get
   * re-pulled. */
  async saveUnitEdits(
    typeName: string,
    patch: { name: string; icon: string; color: string },
    parts: {
      uuid: string | null;
      name: string;
      multiplier: number;
      offset: number;
      is_base: boolean;
    }[],
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
      schema = await this.api.syncUnitParts(schema.name, parts);
      const state = this.getSnapshot();
      const renamed = schema.name !== typeName;
      const tabs = state.tabs.map((tab) =>
        renamed && tab.kind === "type" && tab.name === typeName
          ? { ...tab, name: schema.name }
          : tab,
      );
      const activeTab =
        renamed && state.activeTab?.kind === "type" && state.activeTab.name === typeName
          ? { ...state.activeTab, name: schema.name }
          : state.activeTab;
      this.setState({
        ...state,
        types: state.types.map((view) => (view.name === typeName ? schema : view)),
        tabs,
        activeTab,
      });
      // part renames rewrote stored unit labels across every user type
      for (const view of this.userTypes()) {
        await this.refreshObjectsOf(view.name);
      }
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
          ? { ...tab, name: schema.name }
          : tab,
      );
      const activeTab =
        renamed && state.activeTab?.kind === "type" && state.activeTab.name === typeName
          ? { ...state.activeTab, name: schema.name }
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
          ? { ...tab, name: schema.name }
          : tab,
      );
      const activeTab =
        renamed && state.activeTab?.kind === "type" && state.activeTab.name === typeName
          ? { ...state.activeTab, name: schema.name }
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
      const created = await this.api.createObject(typeName, {
        name: { value: "New Object", unit: null },
      });
      const state = this.getSnapshot();
      const tab: Tab = { kind: "object", uuid: created.uuid, preview: false };
      this.setState({
        ...state,
        objects: [...state.objects, created],
        tabs: state.tabs.some((open) => sameTab(open, tab))
          ? state.tabs
          : [...state.tabs, tab],
        activeTab: tab,
      });
    });
  }

  /** ADR-0008: File/Document/Image exist only via upload — a file is a
   * first-class row, so "new file" is a file pick, not a blank row. */
  async uploadFile(typeName: string, file: File): Promise<FileView | null> {
    let created: FileView | null = null;
    await this.guard(async () => {
      created = await this.api.uploadFile(typeName, file);
      this.setState({
        ...this.getSnapshot(),
        files: [...this.getSnapshot().files, created],
      });
    });
    return created;
  }

  /** Upload an image and return its `img:<uuid>` icon value (ADR-0008).
   * The Image file joins the file list; deleting it later resets icons
   * back to the glyph. */
  async uploadIconImage(file: File): Promise<string> {
    const created = await this.api.uploadFile(TypeNames.IMAGE, file);
    this.setState({
      ...this.getSnapshot(),
      files: [...this.getSnapshot().files, created],
    });
    return `${TypeNames.IMG_ICON_PREFIX}${created.uuid}`;
  }

  /** Rename a file's display name — the uuid pointer is unchanged. */
  async renameFile(uuid: string, name: string): Promise<void> {
    await this.guard(async () => {
      const renamed = await this.api.renameFile(uuid, name);
      this.setState({
        ...this.getSnapshot(),
        files: this.getSnapshot().files.map((f) => (f.uuid === uuid ? renamed : f)),
      });
    });
  }

  /** Delete a file — blobs on disk and array references go with it. */
  async deleteFile(uuid: string): Promise<void> {
    await this.guard(async () => {
      await this.api.deleteFile(uuid);
      this.setState({
        ...this.getSnapshot(),
        files: this.getSnapshot().files.filter((f) => f.uuid !== uuid),
      });
    });
  }

  /** Files of a given file-type (File/Document/Image) for pickers. */
  filesOfType(typeName: string): readonly FileView[] {
    return this.getSnapshot().files.filter((f) => f.type_name === typeName);
  }

  async deleteObject(uuid: string): Promise<void> {
    await this.guard(async () => {
      await this.api.deleteObject(uuid);
      this.setState({
        ...this.getSnapshot(),
        objects: this.getSnapshot().objects.filter((o) => o.uuid !== uuid),
      });
      this.closeTab({ kind: "object", uuid, preview: false });
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

  /** Re-pull one object — tag projections (ADR-0005) change when OTHER
   * objects are edited, so the tag chips re-fetch after every
   * member-side write. */
  async refreshObject(uuid: string): Promise<ObjectView> {
    const fresh = await this.api.getObject(uuid);
    this.setState({
      ...this.getSnapshot(),
      objects: this.getSnapshot().objects.map((o) => (o.uuid === uuid ? fresh : o)),
    });
    return fresh;
  }

  /** ADR-0007: create a Function<T,R> instance and open it as a tab. */
  async createFunction(
    inputType: string,
    outputType: string,
    name: string,
    inputObjectUuid: string | null,
    nodes: FunctionNodeInput[],
    edges: FunctionEdgeInput[],
  ): Promise<void> {
    await this.guard(async () => {
      const created = await this.api.createFunction(
        inputType,
        outputType,
        name,
        inputObjectUuid,
        nodes,
        edges,
      );
      const state = this.getSnapshot();
      const tabs = state.tabs.filter((tab) => tab.kind !== "create-function");
      const tab: Tab = { kind: "function", uuid: created.uuid, preview: false };
      this.setState({
        ...state,
        functions: [...state.functions, created],
        tabs: tabs.some((open) => sameTab(open, tab)) ? tabs : [...tabs, tab],
        activeTab: tab,
      });
    });
  }

  /** ADR-0007: persist a function's DAG/parameterization. Computed props
   * change value on the next read, so every object re-pulls. */
  async saveFunctionEdits(
    uuid: string,
    name: string,
    inputObjectUuid: string | null,
    nodes: FunctionNodeInput[],
    edges: FunctionEdgeInput[],
  ): Promise<void> {
    await this.guard(async () => {
      const updated = await this.api.updateFunction(
        uuid,
        name,
        inputObjectUuid,
        nodes,
        edges,
      );
      this.setState({
        ...this.getSnapshot(),
        functions: this.getSnapshot().functions.map((f) => (f.uuid === uuid ? updated : f)),
      });
      await this.refreshAllObjects();
    });
  }

  /** ADR-0007: deleting a function unbinds every prop that referenced it. */
  async deleteFunction(uuid: string): Promise<void> {
    await this.guard(async () => {
      await this.api.deleteFunction(uuid);
      const types = await this.api.listTypes();
      const state = this.getSnapshot();
      const tabs = state.tabs.filter((tab) => !(tab.kind === "function" && tab.uuid === uuid));
      const activeTab =
        state.activeTab !== null && tabs.some((tab) => sameTab(tab, state.activeTab as Tab))
          ? state.activeTab
          : (tabs[tabs.length - 1] ?? null);
      this.setState({
        ...state,
        functions: state.functions.filter((f) => f.uuid !== uuid),
        types,
        tabs,
        activeTab,
      });
      await this.refreshAllObjects();
    });
  }

  /** ADR-0007: bind/unbind a function on a prop (null unbinds). The
   * server answers with the schema whose prop now carries the uuid. */
  async setPropFunction(
    typeName: string,
    propKey: string,
    functionUuid: string | null,
  ): Promise<void> {
    await this.guard(async () => {
      const updated = await this.api.setPropFunction(typeName, propKey, functionUuid);
      this.setState({
        ...this.getSnapshot(),
        types: this.getSnapshot().types.map((t) => (t.name === typeName ? updated : t)),
      });
      await this.refreshObjectsOf(typeName);
    });
  }

  private async refreshAllObjects(): Promise<void> {
    for (const view of this.userTypes()) {
      await this.refreshObjectsOf(view.name);
    }
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

  /** Pin the active tab — the VS Code preview-tab rule: an italic tab is
   * transient and the next open evicts it; save/edit pins it permanent. */
  pinActiveTab(): void {
    const state = this.getSnapshot();
    const tab = state.activeTab;
    if (tab === null || !tab.preview) {
      return;
    }
    const pinned = { ...tab, preview: false };
    this.setState({
      ...state,
      tabs: state.tabs.map((open) => (sameTab(open, tab) ? pinned : open)),
      activeTab: pinned,
    });
  }

  private activate(tab: Tab): void {
    const state = this.getSnapshot();
    const existing = state.tabs.find((open) => sameTab(open, tab));
    if (existing !== undefined) {
      this.setState({ ...state, activeTab: existing });
      return;
    }
    const active = state.activeTab;
    if (active !== null && active.preview) {
      const tabs = state.tabs.map((open) => (sameTab(open, active) ? tab : open));
      this.setState({ ...state, tabs, activeTab: tab });
      return;
    }
    this.setState({ ...state, tabs: [...state.tabs, tab], activeTab: tab });
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
