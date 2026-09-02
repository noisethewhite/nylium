import type { ObjectView, PropValue, TypeView } from "../contracts";
import { HttpTransport } from "./http-transport";

/** Typed client for the nylium HTTP surface. */
export class NyliumApi extends HttpTransport {
  private static readonly BASE_URL = "/api";

  constructor() {
    super(NyliumApi.BASE_URL);
  }

  listTypes(): Promise<TypeView[]> {
    return this.request("GET", "/types");
  }

  createType(
    name: string,
    pluralName: string,
    props: Record<string, string>,
  ): Promise<TypeView> {
    return this.request("POST", "/types", { name, plural_name: pluralName, props });
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
