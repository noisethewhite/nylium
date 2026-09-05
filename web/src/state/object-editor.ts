import type { ObjectView, PropValue, TagView, TypeView } from "../contracts";
import { PropValues, TypeNames } from "../contracts";
import { ArrayFieldModel, RefFieldModel } from "../fields/composite-fields";
import { EmbeddedFieldModel } from "../fields/embedded-fields";
import { FieldFactory } from "../fields/field-factory";
import { FieldModel } from "../fields/field-model";
import { Observable } from "./observable";
import { WorkspaceStore } from "./workspace";

export interface EditorState {
  readonly object: ObjectView;
  readonly fields: readonly FieldModel[];
  /** Read-only projections: formula- (ADR-0005) and function-backed
   * (ADR-0007) props are computed on read and never edited here. */
  readonly computed: readonly ComputedProp[];
  readonly saving: boolean;
  readonly dirty: boolean;
  readonly error: string | null;
}

export interface ComputedProp {
  readonly key: string;
  readonly valueType: string;
  readonly value: PropValue | undefined;
  readonly formula: string | null;
  readonly functionUuid: string | null;
}

export interface TagCandidate {
  readonly owner: ObjectView;
  readonly propKey: string;
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
    const unitPartsOf = (
      unitTypeName: string,
    ): { readonly base: string; readonly parts: readonly string[] } | null => {
      const view = workspace.typeView(unitTypeName);
      if (view === undefined || view.kind !== "unit") {
        return null;
      }
      const base = view.unit_parts.find((part) => part.is_base);
      if (base === undefined) {
        return null;
      }
      return { base: base.name, parts: view.unit_parts.map((part) => part.name) };
    };
    const embeddedSchemaOf = (typeName: string): TypeView | undefined => {
      const view = workspace.typeView(typeName);
      return view !== undefined && view.embedded ? view : undefined;
    };
    const fields = schema.props
      .filter((prop) => prop.formula === null && prop.function_uuid === null)
      .map((prop) =>
        FieldFactory.create(prop, object.props[prop.key], enumOptionsOf, unitPartsOf, embeddedSchemaOf),
      );
    const computed: ComputedProp[] = schema.props
      .filter((prop) => prop.formula !== null || prop.function_uuid !== null)
      .map((prop) => ({
        key: prop.key,
        valueType: prop.value_type,
        value: object.props[prop.key],
        formula: prop.formula,
        functionUuid: prop.function_uuid,
      }));
    const store = new ObjectEditorStore(
      { object, fields, computed, saving: false, dirty: false, error: null },
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
      // embedded children may have been created lazily — pull their
      // fresh uuids/generated names off the saved object
      for (const field of fields) {
        if (field instanceof EmbeddedFieldModel) {
          field.syncFromWire(updated.props[field.key]);
        }
      }
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

  /** ADR-0005 tag chips — member-side writes against the owner's
   * Array<T> prop. A tag is never stored on the member: adding one
   * appends a ref to the owner's array, removing one deletes exactly
   * that edge. Both re-fetch the member afterwards because its tag
   * projection only changes on the server. */

  /** Every (owner, Array<ThisType> prop) pair that could point at the
   * edited object. Owners are the loaded objects of each user type —
   * the workspace already lists them all. */
  tagCandidates(): readonly TagCandidate[] {
    const object = this.getSnapshot().object;
    const candidates: TagCandidate[] = [];
    for (const view of this.workspace.userTypes()) {
      if (view.embedded) {
        continue;
      }
      for (const prop of view.props) {
        if (TypeNames.elementOf(prop.value_type) !== object.type_name) {
          continue;
        }
        for (const owner of this.workspace.getSnapshot().objects) {
          if (owner.type_name === view.name && owner.uuid !== object.uuid) {
            candidates.push({ owner, propKey: prop.key });
          }
        }
      }
    }
    return candidates;
  }

  async addTag(candidate: TagCandidate): Promise<void> {
    const object = this.getSnapshot().object;
    const owner = await this.workspace.refreshObject(candidate.owner.uuid);
    const current = owner.props[candidate.propKey];
    const items =
      current !== undefined && PropValues.isArray(current) && current.items !== null
        ? current.items
        : [];
    await this.workspace.saveObject(owner.uuid, {
      [candidate.propKey]: {
        items: [...items, { ref: { uuid: object.uuid, type_name: object.type_name } }],
      },
    });
    await this.refreshSelf();
  }

  async removeTag(tag: TagView): Promise<void> {
    const object = this.getSnapshot().object;
    const owner = await this.workspace.refreshObject(tag.owner_uuid);
    const current = owner.props[tag.prop_key];
    if (current === undefined || !PropValues.isArray(current) || current.items === null) {
      return;
    }
    // exactly one edge — a duplicated membership survives as a second chip
    let removed = false;
    const rest = current.items.filter((item) => {
      const hit =
        !removed && PropValues.isRef(item) && item.ref !== null && item.ref.uuid === object.uuid;
      removed = removed || hit;
      return !hit;
    });
    await this.workspace.saveObject(owner.uuid, { [tag.prop_key]: { items: rest } });
    await this.refreshSelf();
  }

  private async refreshSelf(): Promise<void> {
    const fresh = await this.workspace.refreshObject(this.getSnapshot().object.uuid);
    this.setState({ ...this.getSnapshot(), object: fresh });
  }

  /** Candidates of a ref target type for the chip picker — array-level,
   * where no per-item RefFieldModel exists yet. */
  async refOptionsOf(typeName: string): Promise<readonly ObjectView[]> {
    return this.workspace.listObjectsOfType(typeName);
  }

  /** Schema of a user type by name — for type icons next to object
   * names in ref pickers and chips. */
  typeOf(name: string): TypeView | undefined {
    return this.workspace.getSnapshot().types.find((view) => view.name === name);
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
      return;
    }
    if (field instanceof EmbeddedFieldModel) {
      for (const child of field.childFields) {
        await this.fillRefOptions(child);
      }
    }
  }
}
