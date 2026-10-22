import { type FormEvent, useRef, useState } from "react";
import {
  BrowserRouter,
  Link,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";
import { useNameByAgent, useProfileTokens } from "./api";
import { Leaderboard } from "./Leaderboard";
import { ShareCard } from "./ShareCard";
import { TokenCard } from "./TokenCard";

function ProfileTokensResult({ login }: { login: string }) {
  const profileTokens = useProfileTokens(login);
  const nameByAgent = useNameByAgent();
  const cardRef = useRef<HTMLElement>(null);

  if (profileTokens.isPending || nameByAgent.isPending) {
    return (
      <p className="glass animate-pulse rounded-full px-5 py-2 text-muted">
        Reading {login}'s commits…
      </p>
    );
  }
  if (profileTokens.isError) {
    return (
      <p role="alert" className="glass rounded-3xl px-5 py-3 text-rose-200">
        {profileTokens.error.message}
      </p>
    );
  }
  if (nameByAgent.isError) {
    return (
      <p role="alert" className="glass rounded-3xl px-5 py-3 text-rose-200">
        {nameByAgent.error.message}
      </p>
    );
  }
  return (
    <section className="flex flex-col items-center gap-6">
      <TokenCard
        ref={cardRef}
        login={profileTokens.data.login}
        totalTokens={profileTokens.data.totalTokens}
        rarity={profileTokens.data.rarity}
        tokensByAgent={profileTokens.data.tokensByAgent}
        nameByAgent={nameByAgent.data}
      />
      <ShareCard
        login={profileTokens.data.login}
        totalTokens={profileTokens.data.totalTokens}
        cardRef={cardRef}
      />
    </section>
  );
}

function ProfilePage() {
  const { login: submittedLogin = "" } = useParams();
  const [typedLogin, setTypedLogin] = useState(submittedLogin);
  const navigate = useNavigate();

  function submitLogin(event: FormEvent) {
    event.preventDefault();
    const login = typedLogin.trim();
    navigate(login === "" ? "/" : `/${encodeURIComponent(login)}`);
  }

  return (
    <main className="mx-auto flex max-w-xl flex-col items-center gap-8 px-4 py-12">
      <h1 className="bg-gradient-to-br from-white via-white to-white/40 bg-clip-text font-extrabold text-6xl text-transparent tracking-tighter sm:text-7xl">
        GitToken
      </h1>
      <form
        onSubmit={submitLogin}
        className="glass flex w-full items-center gap-2 rounded-full p-1.5 pl-6 focus-within:ring-2 focus-within:ring-white/40"
      >
        <label className="flex flex-1 flex-col">
          <span className="sr-only">GitHub username</span>
          <input
            value={typedLogin}
            onChange={(event) => setTypedLogin(event.target.value)}
            placeholder="GitHub username"
            className="w-full bg-transparent py-2 text-lg text-white outline-none placeholder:text-white/40"
          />
        </label>
        <button
          type="submit"
          className="glass-interactive rounded-full bg-gradient-to-br from-cyan-300 via-violet-400 to-fuchsia-400 px-6 py-3 font-semibold text-night shadow-[inset_0_1px_0_rgb(255_255_255/0.7),0_8px_30px_-6px_rgb(167_139_250/0.8)]"
        >
          Estimate
        </button>
      </form>
      {submittedLogin !== "" && <ProfileTokensResult login={submittedLogin} />}
    </main>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <div className="relative min-h-screen overflow-hidden">
        <div aria-hidden="true" className="fixed inset-0 -z-10">
          <div className="aurora-blob top-[-10%] left-[-10%] size-[55vmax] bg-cyan-500" />
          <div className="aurora-blob top-[20%] right-[-15%] size-[50vmax] bg-violet-600 [animation-delay:-6s]" />
          <div className="aurora-blob bottom-[-20%] left-[20%] size-[45vmax] bg-fuchsia-500 [animation-delay:-12s]" />
        </div>
        <header className="glass sticky top-4 z-10 mx-auto mt-4 flex w-[calc(100%-2rem)] max-w-3xl items-center justify-between rounded-full py-2 pr-2 pl-4">
          <Link
            to="/"
            className="flex items-center gap-2.5 font-bold text-lg tracking-tight"
          >
            <svg viewBox="0 0 32 32" className="size-8" aria-hidden="true">
              <defs>
                <linearGradient id="logo-fill" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stopColor="#67e8f9" />
                  <stop offset="0.5" stopColor="#a78bfa" />
                  <stop offset="1" stopColor="#f0abfc" />
                </linearGradient>
                <linearGradient id="logo-sheen" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="#fff" stopOpacity="0.7" />
                  <stop offset="0.5" stopColor="#fff" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path d="M16 2 29 9v14l-13 7L3 23V9Z" fill="url(#logo-fill)" />
              <path d="M16 2 29 9v14l-13 7L3 23V9Z" fill="url(#logo-sheen)" />
              <path
                d="m12 10-5 6 5 6m8-12 5 6-5 6"
                fill="none"
                stroke="#05060f"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2.5"
              />
            </svg>
            GitToken
          </Link>
          <nav className="flex items-center gap-1 text-sm">
            <Link
              to="/leaderboard"
              className="glass-interactive rounded-full px-4 py-2 text-white/80 hover:text-white"
            >
              Leaderboard
            </Link>
            <a
              href="https://github.com/Lluc24/GitToken"
              className="glass-interactive rounded-full px-4 py-2 text-white/80 hover:text-white"
            >
              GitHub
            </a>
          </nav>
        </header>
        <Routes>
          <Route path="/" element={<ProfilePage />} />
          <Route path="/:login" element={<ProfilePage />} />
          <Route
            path="/leaderboard"
            element={
              <main className="mx-auto max-w-xl px-4 py-12">
                <Leaderboard />
              </main>
            }
          />
          <Route
            path="*"
            element={
              <main className="mx-auto max-w-xl px-4 py-12">
                <h1 className="font-bold text-3xl tracking-tight">
                  Page not found
                </h1>
                <Link to="/" className="text-cyan-300 hover:text-cyan-200">
                  Back to GitToken
                </Link>
              </main>
            }
          />
        </Routes>
        <footer className="mx-auto mt-12 max-w-3xl px-6 py-8 text-center text-muted text-sm">
          <p>
            Thank you to the open-source tools and coding agents behind every
            commit.
          </p>
        </footer>
      </div>
    </BrowserRouter>
  );
}
