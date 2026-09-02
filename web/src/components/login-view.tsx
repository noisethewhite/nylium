import type { ReactElement } from "react";
import { useState } from "react";
import { AuthStore } from "../state/auth";
import { useObservable } from "../state/use-observable";

/** The login screen: one passkey button, plus the bootstrap form for
 * the very first credential (server rejects registration once any
 * credential exists — the error banner shows that). */
export function LoginView(props: { auth: AuthStore }): ReactElement {
  const state = useObservable(props.auth);
  const [registering, setRegistering] = useState(false);
  const [name, setName] = useState("");

  return (
    <div className="login-screen">
      <div className="login-card">
        <span className="brand">nylium</span>
        {state.error !== null && <div className="error-banner">{state.error}</div>}
        <button
          className="button button-primary login-button"
          disabled={state.busy}
          onClick={() => void props.auth.login()}
        >
          {state.busy ? "Waiting for passkey…" : "Sign in with a passkey"}
        </button>
        {registering ? (
          <form
            className="login-register"
            onSubmit={(event) => {
              event.preventDefault();
              void props.auth.register(name.trim() || null);
            }}
          >
            <input
              className="input"
              autoFocus
              placeholder="Your name"
              value={name}
              disabled={state.busy}
              onChange={(event) => setName(event.target.value)}
            />
            <button
              className="button login-button"
              type="submit"
              disabled={state.busy || name.trim() === ""}
            >
              Register passkey
            </button>
          </form>
        ) : (
          <button className="login-link" onClick={() => setRegistering(true)}>
            First time here? Register the owner passkey
          </button>
        )}
      </div>
    </div>
  );
}
