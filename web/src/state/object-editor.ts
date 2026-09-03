import type { ObjectView, PropValue, TypeView } from "../contracts";
import { ArrayFieldModel, RefFieldModel } from "../fields/composite-fields";
import { FieldFactory } from "../fields/field-factory";
import { FieldModel } from "../fields/field-model";
import { Observable } from "./observable";
import { WorkspaceStore } from "./workspace";

export interface EditorState {
  readonly object: ObjectView;
  readonly fields: readonly FieldModel[];
  readonly saving: boolean;
  readonly dirty: boolean;
  readonly error: string | null;
}

/** Draft owner for one open object: field models, ref options,
 * save/delete. Field models are mutable draft objects; every mutation
 * is followed by touch() so React re-reads the snapshot. Server
 * traffic goes through the workspace, like everywhere else. */
export class ObjectEditorStore extends Observable<EditorState> {
  private readonly workspace: WorkspaceStore;

  private constructor(initial: EditorState, workspace: WorkspaceStore) {
    super(initial);
    this.workspace = workspace;
  }

  static create(
    object: ObjectView,
    schema: TypeView,
    workspace: WorkspaceStore,
  ): ObjectEditorStore {
    const enumOptionsOf = (typeName: string): readonly string[] | null => {
      const view = workspace.typeView(typeName);
      if (view === undefined || view.kind !== "enum") {
        return null;
      }
      return view.enum_options.map((option) => option.value);
    };
    const fields = schema.props.map((prop) =>
      FieldFactory.create(prop, object.props[prop.key], enumOptionsOf),
    );
    const store = new ObjectEditorStore(
      { object, fields, saving: false, dirty: false, error: null },
      workspace,
    );
    void store.loadRefOptions();
    return store;
  }

  /** Re-emit the current snapshot after a draft mutation. */
  touch(): void {
    this.setState({ ...this.getSnapshot(), dirty: true });
  }

  addArrayItem(array: ArrayFieldModel): void {
    const item = array.addItem();
    if (item instanceof RefFieldModel) {
      void this.fillRefOptions(item);
    }
    this.touch();
  }

  removeArrayItem(array: ArrayFieldModel, index: number): void {
    array.removeItem(index);
    this.touch();
  }

  async save(): Promise<void> {
    const { object, fields } = this.getSnapshot();
    for (const field of fields) {
      const invalid = field.validationError();
      if (invalid !== null) {
        this.setState({ ...this.getSnapshot(), error: `${field.key}: ${invalid}` });
        return;
      }
    }
    const props: Record<string, PropValue> = {};
    try {
      for (const field of fields) {
        props[field.key] = field.toWire();
      }
    } catch (caught: unknown) {
      const message = caught instanceof Error ? caught.message : String(caught);
      this.setState({ ...this.getSnapshot(), error: message });
      return;
    }
    this.setState({ ...this.getSnapshot(), saving: true, error: null });
    try {
      const updated = await this.workspace.saveObject(object.uuid, props);
      this.setState({
        ...this.getSnapshot(),
        object: updated,
        saving: false,
        dirty: false,
      });
    } catch (caught: unknown) {
      const message = caught instanceof Error ? caught.message : String(caught);
      this.setState({ ...this.getSnapshot(), saving: false, error: message });
    }
  }

  async deleteObject(): Promise<void> {
    await this.workspace.deleteObject(this.getSnapshot().object.uuid);
  }

  /** Candidates of a ref target type for the chip picker — array-level,
   * where no per-item RefFieldModel exists to carry them. */
  async refOptionsOf(typeName: string): Promise<readonly ObjectView[]> {
    return this.workspace.listObjectsOfType(typeName);
  }

  /** Every RefFieldModel (top-level or inside arrays) gets candidates
   * of its target type. */
  private async loadRefOptions(): Promise<void> {
    for (const field of this.getSnapshot().fields) {
      await this.fillRefOptions(field);
    }
    this.setState({ ...this.getSnapshot() });
  }

  private async fillRefOptions(field: FieldModel): Promise<void> {
    if (field instanceof RefFieldModel) {
      field.options = await this.workspace.listObjectsOfType(field.valueType);
      this.setState({ ...this.getSnapshot() });
      return;
    }
    if (field instanceof ArrayFieldModel) {
      for (const item of field.items) {
        await this.fillRefOptions(item);
      }
    }
  }
}
