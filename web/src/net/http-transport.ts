/** Shared fetch behavior for API clients — extend, don't reimplement. */

export type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

export class HttpError extends Error {
  readonly status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "HttpError";
    this.status = status;
  }
}

export abstract class HttpTransport {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;

  protected constructor(baseUrl: string, fetchImpl?: typeof fetch) {
    this.baseUrl = baseUrl;
    this.fetchImpl = fetchImpl ?? globalThis.fetch.bind(globalThis);
  }

  protected async request<TResponse>(
    method: HttpMethod,
    path: string,
    body?: unknown,
  ): Promise<TResponse> {
    const response = await this.send(method, path, body);
    // trust boundary: the server honors the response models declared
    // in nylium.server — this cast states that contract
    return (await response.json()) as TResponse;
  }

  protected async requestVoid(method: HttpMethod, path: string): Promise<void> {
    await this.send(method, path);
  }

  private async send(method: HttpMethod, path: string, body?: unknown): Promise<Response> {
    const init: RequestInit = { method };
    if (body !== undefined) {
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(body);
    }
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, init);
    if (!response.ok) {
      throw new HttpError(response.status, await HttpTransport.readDetail(response));
    }
    return response;
  }

  private static async readDetail(response: Response): Promise<string> {
    const payload: unknown = await response.json().catch(() => null);
    if (
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof payload.detail === "string"
    ) {
      return payload.detail;
    }
    return response.statusText;
  }
}
