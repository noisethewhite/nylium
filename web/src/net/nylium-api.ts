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
  ): Promise<TypeView> {
    return this.request("POST", "/types", {
      name, plural_name: pluralName, props, icon, color,
    });
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

  createObject(typeName: string, props: Record<string, PropValue>): Promise<ObjectView> {
    return this.request("POST", "/objects", { type_name: typeName, props });
  }

  updateObject(uuid: string, props: Record<string, PropValue>): Promise<ObjectView> {
    return this.request("PATCH", `/objects/${uuid}`, { props });
  }

  deleteObject(uuid: string): Promise<void> {
    return this.requestVoid("DELETE", `/objects/${uuid}`);
  }
}
