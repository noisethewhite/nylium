/** ADR-0004: an embedded (composition) prop — the child object is
 * edited inline through this model; its fields are ordinary
 * FieldModels built from the child type's schema. The pinned `name`
 * prop is server-generated and never editable here. */
import type { EmbeddedValue, PropValue, TypeView } from "../contracts";
import { PropValues } from "../contracts";
import type { EnumOptionsOf } from "./enum-fields";
import { FieldFactory } from "./field-factory";
import { FieldModel } from "./field-model";
import type { UnitPartsOf } from "./unit-fields";

/** Resolves an embedded type name to its schema — the workspace
 * builds it; the fields layer never sees the store. */
export type EmbeddedSchemaOf = (typeName: string) => TypeView | undefined;

export class EmbeddedFieldModel extends FieldModel {
  /** The child type's schema — drives the nested field set. */
  readonly schema: TypeView;
  /** null = the child does not exist yet (created lazily on save). */
  childUuid: string | null;
  /** Server-generated child name, shown read-only. */
  childName: string | null;
  childFields: FieldModel[];
  readonly enumOptionsOf: EnumOptionsOf | undefined;
  readonly unitPartsOf: UnitPartsOf | undefined;
  readonly embeddedSchemaOf: EmbeddedSchemaOf | undefined;

  constructor(
    key: string,
    valueType: string,
    schema: TypeView,
    childUuid: string | null,
    childName: string | null,
    childFields: FieldModel[],
    enumOptionsOf?: EnumOptionsOf,
    unitPartsOf?: UnitPartsOf,
    embeddedSchemaOf?: EmbeddedSchemaOf,
  ) {
    super(key, valueType);
    this.schema = schema;
    this.childUuid = childUuid;
    this.childName = childName;
    this.childFields = childFields;
    this.enumOptionsOf = enumOptionsOf;
    this.unitPartsOf = unitPartsOf;
    this.embeddedSchemaOf = embeddedSchemaOf;
  }

  static fromWire(
    key: string,
    valueType: string,
    schema: TypeView,
    value: PropValue | undefined,
    enumOptionsOf?: EnumOptionsOf,
    unitPartsOf?: UnitPartsOf,
    embeddedSchemaOf?: EmbeddedSchemaOf,
  ): EmbeddedFieldModel {
    const embedded =
      value !== undefined && PropValues.isEmbedded(value) ? value : null;
    return new EmbeddedFieldModel(
      key,
      valueType,
      schema,
      embedded?.uuid ?? null,
      EmbeddedFieldModel.nameOf(embedded?.props),
      EmbeddedFieldModel.buildFields(
        schema,
        embedded?.props,
        enumOptionsOf,
        unitPartsOf,
        embeddedSchemaOf,
      ),
      enumOptionsOf,
      unitPartsOf,
      embeddedSchemaOf,
    );
  }

  /** Post-save reconciliation: the child may have been created lazily
   * — pull its fresh uuid and generated name off the saved object. */
  syncFromWire(value: PropValue | undefined): void {
    if (value === undefined || !PropValues.isEmbedded(value)) {
      return;
    }
    this.childUuid = value.uuid;
    this.childName = EmbeddedFieldModel.nameOf(value.props) ?? this.childName;
  }

  private static nameOf(
    props: Record<string, PropValue> | undefined,
  ): string | null {
    const nameWire = props?.["name"];
    return nameWire !== undefined &&
      PropValues.isScalar(nameWire) &&
      typeof nameWire.value === "string"
      ? nameWire.value
      : null;
  }

  private static buildFields(
    schema: TypeView,
    props: Record<string, PropValue> | undefined,
    enumOptionsOf?: EnumOptionsOf,
    unitPartsOf?: UnitPartsOf,
    embeddedSchemaOf?: EmbeddedSchemaOf,
  ): FieldModel[] {
    return schema.props
      .filter((prop) => prop.key !== "name")
      .map((prop) =>
        FieldFactory.createForType(
          prop.key,
          prop.value_type,
          props?.[prop.key],
          enumOptionsOf,
          unitPartsOf,
          embeddedSchemaOf,
        ),
      );
  }

  /** A wire value that carries no data: unset scalars (boolean false
   * counts as unset — an untouched checkbox must not lazy-create a
   * child), unset refs, empty arrays, empty nested embeds. */
  private static isEmptyWire(value: PropValue): boolean {
    if (PropValues.isScalar(value)) {
      return value.value === null || value.value === false;
    }
    if (PropValues.isRef(value)) {
      return value.ref === null;
    }
    if (PropValues.isArray(value)) {
      return value.items === null || value.items.length === 0;
    }
    return Object.keys(value.props).length === 0;
  }

  override validationError(): string | null {
    for (const child of this.childFields) {
      const error = child.validationError();
      if (error !== null) {
        return error;
      }
    }
    return null;
  }

  toWire(): EmbeddedValue {
    const props: Record<string, PropValue> = {};
    for (const child of this.childFields) {
      props[child.key] = child.toWire();
    }
    // an all-empty draft means "no value": it never lazy-creates, and
    // for an existing child it is the prop clear that cascades delete
    if (Object.values(props).every(EmbeddedFieldModel.isEmptyWire)) {
      return { uuid: this.childUuid, type_name: this.valueType, props: {} };
    }
    return { uuid: this.childUuid, type_name: this.valueType, props };
  }
}
