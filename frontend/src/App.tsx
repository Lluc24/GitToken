import { type FormEvent, useState } from "react";
import { AgentTokens } from "./AgentTokens";
import { useProfileTokens } from "./api";
import { TokenCard } from "./TokenCard";

function loginFromUrl(): string {
  return new URLSearchParams(window.location.search).get("login") ?? "";
}

function ProfileTokensResult({ login }: { login: string }) {
  const profileTokens = useProfileTokens(login);

  if (profileTokens.isPending) {
    return <p>Reading {login}'s commits…</p>;
  }
  if (profileTokens.isError) {
    return <p role="alert">{profileTokens.error.message}</p>;
  }
  return (
    <section className="flex flex-col items-center gap-6">
      <TokenCard
        login={profileTokens.data.login}
        totalTokens={profileTokens.data.totalTokens}
        rarity={profileTokens.data.rarity}
      />
      <AgentTokens tokensByAgent={profileTokens.data.tokensByAgent} />
    </section>
  );
}

export function App() {
  const [typedLogin, setTypedLogin] = useState(loginFromUrl);
  const [submittedLogin, setSubmittedLogin] = useState(loginFromUrl);

  function submitLogin(event: FormEvent) {
    event.preventDefault();
    const login = typedLogin.trim();
    setSubmittedLogin(login);
    const url = login === "" ? "/" : `/?login=${encodeURIComponent(login)}`;
    window.history.replaceState(null, "", url);
  }

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-4xl items-center justify-between px-6 py-6">
        <a
          href="/"
          className="flex items-center gap-3 font-bold font-display text-2xl tracking-tight"
        >
          <svg
            viewBox="0 0 32 32"
            className="size-9 text-scout-green"
            aria-hidden="true"
          >
            <path d="M16 2 29 9v14l-13 7L3 23V9Z" fill="currentColor" />
            <path
              d="m12 10-5 6 5 6m8-12 5 6-5 6"
              fill="none"
              stroke="#071a25"
              strokeWidth="2.5"
            />
          </svg>
          GitToken
        </a>
        <a
          href="https://github.com/Lluc24/GitToken"
          className="text-muted hover:text-white"
        >
          GitHub
        </a>
      </header>
      <main className="mx-auto flex max-w-xl flex-col items-center gap-8 px-4 py-12">
        <h1 className="font-bold font-display text-6xl uppercase tracking-tight">
          GitToken
        </h1>
        <form
          onSubmit={submitLogin}
          className="flex w-full flex-col gap-3 sm:flex-row sm:items-end"
        >
          <label className="flex flex-1 flex-col gap-1 font-display text-muted text-sm uppercase tracking-[0.2em]">
            GitHub username
            <input
              value={typedLogin}
              onChange={(event) => setTypedLogin(event.target.value)}
              className="rounded-2xl border border-white/15 bg-pitch-night/60 px-4 py-3 font-mono text-base text-white tracking-normal outline-none focus:border-card-gold"
            />
          </label>
          <button
            type="submit"
            className="rounded-2xl bg-scout-green px-6 py-3 font-bold font-display text-lg text-pitch-night uppercase tracking-wider hover:brightness-110"
          >
            Estimate tokens
          </button>
        </form>
        {submittedLogin !== "" && (
          <ProfileTokensResult login={submittedLogin} />
        )}
      </main>
      <footer className="mx-auto mt-12 max-w-4xl border-t border-white/10 px-6 py-8 text-muted text-sm">
        <p>
          Thank you to the open-source tools and coding agents behind every
          commit.
        </p>
      </footer>
    </div>
  );
}
