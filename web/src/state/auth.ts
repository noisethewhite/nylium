import { startAuthentication, startRegistration, WebAuthnError } from "@simplewebauthn/browser";
import { AuthApi } from "../net/auth-api";
import type { UserView } from "../net/auth-api";
import { HttpError } from "../net/http-transport";
import { Observable } from "./observable";

export type AuthStatus = "loading" | "anonymous" | "authenticated";

export interface AuthState {
  readonly status: AuthStatus;
  readonly userName: string | null;
  readonly busy: boolean;
  readonly error: string | null;
}

const INITIAL_STATE: AuthState = {
  status: "loading",
  userName: null,
  busy: false,
  error: null,
};

/** Session source of truth: who is signed in, ceremony in flight,
 * last failure. The SPA is the login screen — the guard lives
 * server-side, this store only reflects it. */
export class AuthStore extends Observable<AuthState> {
  private readonly api: AuthApi;

  constructor(api: AuthApi) {
    super(INITIAL_STATE);
    this.api = api;
  }

  /** Boot probe: a live session cookie restores the session silently.
   * A 401 is simply "no session"; anything else (network down, 5xx) is
   * a diagnosis the login screen must show, not swallow. */
  async init(): Promise<void> {
    try {
      const user = await this.api.me();
      this.setState({
        ...this.getSnapshot(),
        status: "authenticated",
        userName: user.name,
      });
    } catch (caught: unknown) {
      if (caught instanceof HttpError && caught.status === 401) {
        this.setState({ ...this.getSnapshot(), status: "anonymous" });
        return;
      }
      const message = caught instanceof Error ? caught.message : String(caught);
      this.setState({ ...this.getSnapshot(), status: "anonymous", error: message });
    }
  }

  async login(): Promise<void> {
    await this.ceremony(async () => {
      const options = await this.api.loginStart();
      const credential = await startAuthentication({ optionsJSON: options });
      return this.api.loginFinish(credential);
    });
  }

  async register(name: string | null): Promise<void> {
    await this.ceremony(async () => {
      const options = await this.api.registerStart(name);
      const credential = await startRegistration({ optionsJSON: options });
      return this.api.registerFinish(credential);
    });
  }

  /** Local session drop always wins; a failed server call is already
   * toasted by the transport's error reporter, so we don't swallow it
   * silently — we just don't let it block the sign-out. */
  async logout(): Promise<void> {
    await this.api.logout().catch(() => undefined);
    this.expire();
  }

  /** Session died mid-flight (401 from any API call) — drop to login. */
  expire(): void {
    this.setState({ status: "anonymous", userName: null, busy: false, error: null });
  }

  private async ceremony(run: () => Promise<UserView>): Promise<void> {
    this.setState({ ...this.getSnapshot(), busy: true, error: null });
    try {
      const user = await run();
      this.setState({
        status: "authenticated",
        userName: user.name,
        busy: false,
        error: null,
      });
    } catch (caught: unknown) {
      let message = "Passkey ceremony failed";
      if (caught instanceof WebAuthnError || caught instanceof HttpError) {
        message = caught.message;
      }
      this.setState({ ...this.getSnapshot(), busy: false, error: message });
    }
  }
}
