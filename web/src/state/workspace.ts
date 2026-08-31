import type { ObjectView, PropValue, TypeView } from "../contracts";
import { TypeNames } from "../contracts";
import { WhiteoutApi } from "../net/whiteout-api";
import { Observable } from "./observable";

export interface WorkspaceState {
  readonly loading: boolean;
  readonly types: readonly TypeView[];
  readonly selectedTypeName: string | null;
  readonly objects: readonly ObjectView[];
  readonly selectedObjectUuid: string | null;
  readonly error: string | null;
}

const INITIAL_STATE: WorkspaceState = {
  loading: true,
  types: [],
  selectedTypeName: null,
  objects: [],
  selectedObjectUuid: null,
  error: null,
};

/** The screen's source of truth: which type is open, its objects,
 * which object is being edited. All server traffic funnels through
 * here — components only call actions. */
export class WorkspaceStore extends Observable<WorkspaceState> {
  private readonly api: WhiteoutApi;

  constructor(api: WhiteoutApi) {
    super(INITIAL_STATE);
    this.api = api;
  }

  async init(): Promise<void> {
    await this.guard(async () => {
      const types = await this.api.listTypes();
      const selected = types.find((view) => TypeNames.isUserType(view.name)) ?? null;
      this.setState({ ...this.getSnapshot(), loading: false, types });
      if (selected !== null) {
        await this.selectType(selected.name);
      }
    });
  }

  async selectType(name: string): Promise<void> {
    this.setState({
      ...this.getSnapshot(),
      selectedTypeName: name,
      selectedObjectUuid: null,
      objects: [],
    });
    await this.guard(async () => this.refreshObjects());
  }

  async selectObject(uuid: string | null): Promise<void> {
    this.setState({ ...this.getSnapshot(), selectedObjectUuid: uuid });
  }

  async createType(name: string, props: Record<string, string>): Promise<void> {
    await this.guard(async () => {
      const created = await this.api.createType(name, props);
      const types = [...this.getSnapshot().types, created];
      this.setState({
        ...this.getSnapshot(),
        types,
        selectedTypeName: created.name,
        selectedObjectUuid: null,
        objects: [],
      });
    });
  }

  async deleteType(name: string): Promise<void> {
    await this.guard(async () => {
      await this.api.deleteType(name);
      const state = this.getSnapshot();
      const types = state.types.filter((view) => view.name !== name);
      this.setState({
        ...state,
        types,
        selectedTypeName: state.selectedTypeName === name ? null : state.selectedTypeName,
        objects: state.selectedTypeName === name ? [] : state.objects,
        selectedObjectUuid: state.selectedTypeName === name ? null : state.selectedObjectUuid,
      });
    });
  }

  async createObject(): Promise<void> {
    const typeName = this.getSnapshot().selectedTypeName;
    if (typeName === null) {
      return;
    }
    await this.guard(async () => {
      const created = await this.api.createObject(typeName, {});
      await this.refreshObjects();
      this.setState({ ...this.getSnapshot(), selectedObjectUuid: created.uuid });
    });
  }

  async deleteObject(uuid: string): Promise<void> {
    await this.guard(async () => {
      await this.api.deleteObject(uuid);
      await this.refreshObjects();
      this.setState({ ...this.getSnapshot(), selectedObjectUuid: null });
    });
  }

  async refreshObjects(): Promise<void> {
    const typeName = this.getSnapshot().selectedTypeName;
    if (typeName === null) {
      return;
    }
    const objects = await this.api.listObjects(typeName);
    this.setState({ ...this.getSnapshot(), objects });
  }

  selectedType(): TypeView | null {
    const { types, selectedTypeName } = this.getSnapshot();
    return types.find((view) => view.name === selectedTypeName) ?? null;
  }

  userTypes(): readonly TypeView[] {
    return this.getSnapshot().types.filter((view) => TypeNames.isUserType(view.name));
  }

  /** Read-through for the editor's ref pickers — components never
   * touch the transport directly. */
  listObjectsOfType(typeName: string): Promise<ObjectView[]> {
    return this.api.listObjects(typeName);
  }

  /** The editor's save path — writes through, then resyncs the list. */
  async saveObject(uuid: string, props: Record<string, PropValue>): Promise<ObjectView> {
    const updated = await this.api.updateObject(uuid, props);
    await this.refreshObjects();
    return updated;
  }

  private async guard(action: () => Promise<void>): Promise<void> {
    try {
      await action();
      this.setState({ ...this.getSnapshot(), error: null });
    } catch (caught: unknown) {
      const message = caught instanceof Error ? caught.message : String(caught);
      this.setState({ ...this.getSnapshot(), error: message });
    }
  }
}
