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
    <main className="mx-auto flex max-w-xl flex-col items-center gap-8 px-4 py-12">
      <h1 className="font-display text-6xl text-crown-gold [text-shadow:0_4px_0_var(--color-crown-gold-dark),0_6px_12px_rgb(0_0_0/0.6)]">
        GitToken
      </h1>
      <form
        onSubmit={submitLogin}
        className="flex w-full flex-col gap-3 sm:flex-row sm:items-end"
      >
        <label className="flex flex-1 flex-col gap-1 font-display text-lg">
          GitHub username
          <input
            value={typedLogin}
            onChange={(event) => setTypedLogin(event.target.value)}
            className="rounded-xl border-4 border-arena-night bg-white px-4 py-2 font-sans text-arena-night shadow-inner outline-none focus:border-crown-gold"
          />
        </label>
        <button
          type="submit"
          className="rounded-xl border-4 border-arena-night bg-gradient-to-b from-crown-gold to-crown-gold-dark px-6 py-2 font-display text-xl shadow-[0_4px_0_var(--color-arena-night)] [text-shadow:0_2px_0_rgb(0_0_0/0.5)] active:translate-y-1 active:shadow-none"
        >
          Estimate tokens
        </button>
      </form>
      {submittedLogin !== "" && <ProfileTokensResult login={submittedLogin} />}
    </main>
  );
}
