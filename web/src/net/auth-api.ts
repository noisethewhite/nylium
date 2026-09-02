import type {
  AuthenticationResponseJSON,
  PublicKeyCredentialCreationOptionsJSON,
  PublicKeyCredentialRequestOptionsJSON,
  RegistrationResponseJSON,
} from "@simplewebauthn/browser";
import { HttpTransport } from "./http-transport";

export interface UserView {
  readonly uuid: string;
  readonly name: string;
}

/** Client for /api/auth — passkey ceremonies over the session cookie. */
export class AuthApi extends HttpTransport {
  constructor() {
    super("/api/auth");
  }

  me(): Promise<UserView> {
    return this.request("GET", "/me");
  }

  loginStart(): Promise<PublicKeyCredentialRequestOptionsJSON> {
    return this.request("POST", "/login/start");
  }

  loginFinish(credential: AuthenticationResponseJSON): Promise<UserView> {
    return this.request("POST", "/login/finish", credential);
  }

  registerStart(name: string | null): Promise<PublicKeyCredentialCreationOptionsJSON> {
    return this.request("POST", "/register/start", { name });
  }

  registerFinish(credential: RegistrationResponseJSON): Promise<UserView> {
    return this.request("POST", "/register/finish", credential);
  }

  logout(): Promise<void> {
    return this.requestVoid("POST", "/logout");
  }
}
