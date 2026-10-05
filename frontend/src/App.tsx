import { type FormEvent, useState } from "react";
import { type ProfileTokens, useProfileTokens, useRarity } from "./api";
import { formatTokens } from "./format";
import { TokenCard } from "./TokenCard";

function ProfileTokensCard({
  profileTokens,
}: {
  profileTokens: ProfileTokens;
}) {
  const rarity = useRarity(profileTokens.totalTokens);

  if (rarity.isPending) {
    return <p>Picking {profileTokens.login}'s card…</p>;
  }
  if (rarity.isError) {
    return <p role="alert">{rarity.error.message}</p>;
  }
  return (
    <TokenCard
      login={profileTokens.login}
      totalTokens={profileTokens.totalTokens}
      rarity={rarity.data}
    />
  );
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
      <ProfileTokensCard profileTokens={profileTokens.data} />
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
      {submittedLogin !== "" && <ProfileTokensResult login={submittedLogin} />}
    </main>
  );
}
