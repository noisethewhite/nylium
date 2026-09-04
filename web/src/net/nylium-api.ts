import type { ObjectView, PropValue, TypeView } from "../contracts";
import type { ErrorReporter } from "./http-transport";
import { HttpTransport } from "./http-transport";

/** Typed client for the nylium HTTP surface. */
export class NyliumApi extends HttpTransport {
  private static readonly BASE_URL = "/api";

  constructor(onError?: ErrorReporter) {
    super(NyliumApi.BASE_URL, undefined, onError);
  }

  listTypes(): Promise<TypeView[]> {
    return this.request("GET", "/types");
  }

  createType(
    name: string,
    pluralName: string,
    props: Record<string, string>,
    icon?: string,
    color?: string,
    embedded?: boolean,
  ): Promise<TypeView> {
    return this.request("POST", "/types", {
      name, plural_name: pluralName, props, icon, color, embedded,
    });
  }

  createEnum(name: string, options: string[]): Promise<TypeView> {
    return this.request("POST", "/enums", { name, options });
  }

  /** Full option draft: {uuid, value} renames (propagating to stored
   * values), uuid null creates, absent uuids delete unless in use. */
  syncEnumOptions(
    name: string,
    options: { uuid: string | null; value: string }[],
  ): Promise<TypeView> {
    return this.request<TypeView>(
      "PUT", `/enums/${encodeURIComponent(name)}/options`, { options },
    );
  }

  /** A unit type: name, its base part, optional secondary parts with
   * the affine factor (base = (entered - offset) / multiplier). */
  createUnit(
    name: string,
    base: string,
    secondaries: { name: string; multiplier: number; offset: number }[],
  ): Promise<TypeView> {
    return this.request("POST", "/units", { name, base, secondaries });
  }

  /** Full part draft — same semantics as syncEnumOptions: uuid renames
   * propagate into stored unit labels, uuid null creates, absent uuids
   * delete unless in use. Exactly one part must carry is_base. */
  syncUnitParts(
    name: string,
    parts: {
      uuid: string | null;
      name: string;
      multiplier: number;
      offset: number;
      is_base: boolean;
    }[],
  ): Promise<TypeView> {
    return this.request<TypeView>(
      "PUT", `/units/${encodeURIComponent(name)}/parts`, { parts },
    );
  }

  /** Persist a new prop order — keys must cover the whole schema. */
  reorderProps(typeName: string, keys: string[]): Promise<TypeView> {
    return this.request<TypeView>(
      "PATCH", `/types/${encodeURIComponent(typeName)}/props-order`, { keys },
    );
  }

  syncProps(
    typeName: string,
    props: { uuid: string | null; key: string; value_type: string }[],
  ): Promise<TypeView> {
    return this.request<TypeView>(
      "PUT", `/types/${encodeURIComponent(typeName)}/props`, { props },
    );
  }

  updateType(
    name: string,
    patch: { name?: string; plural_name?: string; icon?: string; color?: string },
  ): Promise<TypeView> {
    return this.request<TypeView>(
      "PATCH", `/types/${encodeURIComponent(name)}`, patch,
    );
  }

  deleteType(name: string): Promise<void> {
    return this.requestVoid("DELETE", `/types/${encodeURIComponent(name)}`);
  }

  listObjects(typeName: string): Promise<ObjectView[]> {
    return this.request("GET", `/objects?type_name=${encodeURIComponent(typeName)}`);
  }

  getObject(uuid: string): Promise<ObjectView> {
    return this.request("GET", `/objects/${encodeURIComponent(uuid)}`);
  }

  createObject(typeName: string, props: Record<string, PropValue>): Promise<ObjectView> {
    return this.request("POST", "/objects", { type_name: typeName, props });
  }

  updateObject(uuid: string, props: Record<string, PropValue>): Promise<ObjectView> {
    return this.request("PATCH", `/objects/${uuid}`, { props });
  }

  deleteObject(uuid: string): Promise<void> {
    return this.requestVoid("DELETE", `/objects/${uuid}`);
  }

  /** ADR-0006: upload a blob as a File/Document/Image instance. The
   * multipart body carries the bytes; the instance is a uuid-stable
   * pointer, so renaming the object never breaks references. */
  async uploadFile(typeName: string, file: File): Promise<ObjectView> {
    const form = new FormData();
    form.append("file", file, file.name);
    const response = await fetch(
      `${NyliumApi.BASE_URL}/files?type_name=${encodeURIComponent(typeName)}`,
      { method: "POST", body: form, credentials: "same-origin" },
    );
    if (!response.ok) {
      throw new Error(`upload failed: ${response.status} ${await response.text()}`);
    }
    return (await response.json()) as ObjectView;
  }

  /** Blob URL for previews/downloads — served from GET /api/files/{uuid}. */
  static fileUrl(uuid: string): string {
    return `/api/files/${encodeURIComponent(uuid)}`;
  }
}
