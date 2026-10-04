import { type FormEvent, useState } from "react";
import { useProfileTokens } from "./api";
import { formatTokens } from "./format";

function ProfileTokensResult({ login }: { login: string }) {
  const profileTokens = useProfileTokens(login);

  if (profileTokens.isPending) {
    return <p>Reading {login}'s commits…</p>;
  }
  if (profileTokens.isError) {
    return <p role="alert">{profileTokens.error.message}</p>;
  }
  return (
    <section>
      <h2>
        {profileTokens.data.login}:{" "}
        {formatTokens(profileTokens.data.totalTokens)} tokens
      </h2>
      <ul>
        {Object.entries(profileTokens.data.tokensByAgent).map(
          ([agent, tokens]) => (
            <li key={agent}>
              {agent}: {formatTokens(tokens)}
            </li>
          ),
        )}
      </ul>
    </section>
  );
}

export function App() {
  const [typedLogin, setTypedLogin] = useState("");
  const [submittedLogin, setSubmittedLogin] = useState("");

  function submitLogin(event: FormEvent) {
    event.preventDefault();
    setSubmittedLogin(typedLogin.trim());
  }

  return (
    <main>
      <h1>GitToken</h1>
      <form onSubmit={submitLogin}>
        <label>
          GitHub username{" "}
          <input
            value={typedLogin}
            onChange={(event) => setTypedLogin(event.target.value)}
          />
        </label>{" "}
        <button type="submit">Estimate tokens</button>
      </form>
      {submittedLogin !== "" && <ProfileTokensResult login={submittedLogin} />}
    </main>
  );
}
