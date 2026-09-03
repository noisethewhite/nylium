/** Shared fetch behavior for API clients — extend, don't reimplement. */

export type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
/** Sink for transport-level failures — every non-2xx lands here once. */
export type ErrorReporter = (error: HttpError) => void;

export class HttpError extends Error {
  readonly status: number;
  /** Machine code from {"error": {"code": …}} — empty when the server
   * answered with something else (proxy pages, stale builds). */
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.code = code;
  }
}

export abstract class HttpTransport {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  private readonly onError: ErrorReporter | null;

  protected constructor(
    baseUrl: string,
    fetchImpl?: typeof fetch,
    onError?: ErrorReporter,
  ) {
    this.baseUrl = baseUrl;
    this.fetchImpl = fetchImpl ?? globalThis.fetch.bind(globalThis);
    this.onError = onError ?? null;
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
    let response: Response;
    try {
      response = await this.fetchImpl(`${this.baseUrl}${path}`, init);
    } catch {
      // fetch itself threw — DNS, connection reset, server down
      const error = new HttpError(0, "network", "server unreachable");
      this.report(error);
      throw error;
    }
    if (!response.ok) {
      const error = await HttpTransport.readError(response);
      this.report(error);
      throw error;
    }
    return response;
  }

  private report(error: HttpError): void {
    // 401 is a session transition, not a failure — the auth store
    // flips the screen; no log noise
    if (this.onError !== null && error.status !== 401) {
      this.onError(error);
    }
  }

  /** The backend's uniform shape is {"error": {"code", "message"}};
   * older payloads carry {"detail": …}; anything else falls back to
   * the status line. */
  private static async readError(response: Response): Promise<HttpError> {
    const payload: unknown = await response.json().catch(() => null);
    if (typeof payload === "object" && payload !== null && "error" in payload) {
      const embedded = payload.error;
      if (
        typeof embedded === "object" &&
        embedded !== null &&
        "code" in embedded &&
        typeof embedded.code === "string" &&
        "message" in embedded &&
        typeof embedded.message === "string"
      ) {
        return new HttpError(response.status, embedded.code, embedded.message);
      }
    }
    if (
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof payload.detail === "string"
    ) {
      return new HttpError(response.status, "", payload.detail);
    }
    return new HttpError(response.status, "", response.statusText);
  }
}
