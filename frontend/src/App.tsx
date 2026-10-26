import {
  BrowserRouter,
  Link,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";
import { useProfileTokens } from "./api";
import { BadgesPage } from "./BadgesPage";
import { profileCardPath } from "./badges";
import { formatTokens } from "./format";
import { glassClassName, pressableClassName } from "./glass";
import { Leaderboard } from "./Leaderboard";
import { LoginForm } from "./LoginForm";
import { ShareCard } from "./ShareCard";
import { ThemeToggle } from "./ThemeToggle";
import { useTheme } from "./theme";

function ProfileTokensResult({ login }: { login: string }) {
  const profileTokens = useProfileTokens(login);
  const theme = useTheme();

  if (profileTokens.isPending) {
    return (
      <p
        className={`animate-pulse rounded-full px-5 py-2 text-night/60 dark:text-white/60 ${glassClassName}`}
      >
        Reading {login}'s commits…
      </p>
    );
  }
  if (profileTokens.isError) {
    return (
      <p
        role="alert"
        className={`rounded-3xl px-5 py-3 text-rose-700 dark:text-rose-200 ${glassClassName}`}
      >
        {profileTokens.error.message}
      </p>
    );
  }
  const { data } = profileTokens;
  return (
    <section className="flex flex-col items-center gap-6">
      <img
        src={profileCardPath(data.login, theme)}
        alt={`${data.login}: ${formatTokens(data.totalTokens)} estimated tokens, ${data.rarity}`}
        width={300}
        className="drop-shadow-[0_24px_40px_rgb(15_23_42/0.18)] dark:drop-shadow-[0_30px_50px_rgb(0_0_0/0.6)]"
      />
      <ShareCard login={data.login} totalTokens={data.totalTokens} />
    </section>
  );
}

function ProfilePage() {
  const { login: submittedLogin = "" } = useParams();
  const navigate = useNavigate();

  return (
    <main className="mx-auto flex max-w-xl flex-col items-center gap-8 px-4 py-12">
      <h1 className="bg-gradient-to-br from-night dark:from-white via-night dark:via-white to-night/40 dark:to-white/40 bg-clip-text font-extrabold text-6xl text-transparent tracking-tighter sm:text-7xl">
        GitToken
      </h1>
      <LoginForm
        key={submittedLogin}
        initialLogin={submittedLogin}
        submitLabel="Estimate"
        onSubmitLogin={(login) =>
          navigate(login === "" ? "/" : `/${encodeURIComponent(login)}`)
        }
      />
      {submittedLogin !== "" && <ProfileTokensResult login={submittedLogin} />}
    </main>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <div className="relative min-h-screen overflow-hidden">
        <div aria-hidden="true" className="fixed inset-0 -z-10">
          <div className="absolute animate-drift rounded-full opacity-55 blur-[90px] motion-reduce:animate-none top-[-10%] left-[-10%] size-[55vmax] bg-cyan-300 dark:bg-cyan-500" />
          <div className="absolute animate-drift rounded-full opacity-55 blur-[90px] motion-reduce:animate-none top-[20%] right-[-15%] size-[50vmax] bg-violet-300 dark:bg-violet-600 [animation-delay:-6s]" />
          <div className="absolute animate-drift rounded-full opacity-55 blur-[90px] motion-reduce:animate-none bottom-[-20%] left-[20%] size-[45vmax] bg-pink-300 dark:bg-fuchsia-500 [animation-delay:-12s]" />
        </div>
        <header
          className={`sticky top-4 z-10 mx-auto mt-4 flex w-[calc(100%-2rem)] max-w-3xl items-center justify-between rounded-full py-2 pr-2 pl-4 ${glassClassName}`}
        >
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
              className={`rounded-full px-4 py-2 text-night/80 dark:text-white/80 hover:bg-night/15 dark:hover:bg-white/15 hover:text-night dark:hover:text-white ${pressableClassName}`}
            >
              Leaderboard
            </Link>
            <Link
              to="/badges"
              className={`rounded-full px-4 py-2 text-night/80 dark:text-white/80 hover:bg-night/15 dark:hover:bg-white/15 hover:text-night dark:hover:text-white ${pressableClassName}`}
            >
              Badges
            </Link>
            <a
              href="https://github.com/Lluc24/GitToken"
              className={`rounded-full px-4 py-2 text-night/80 dark:text-white/80 hover:bg-night/15 dark:hover:bg-white/15 hover:text-night dark:hover:text-white ${pressableClassName}`}
            >
              GitHub
            </a>
            <ThemeToggle />
          </nav>
        </header>
        <Routes>
          <Route path="/" element={<ProfilePage />} />
          <Route path="/:login" element={<ProfilePage />} />
          <Route path="/badges" element={<BadgesPage />} />
          <Route path="/:login/badges" element={<BadgesPage />} />
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
                <Link
                  to="/"
                  className="text-cyan-700 hover:text-cyan-600 dark:text-cyan-300 dark:hover:text-cyan-200"
                >
                  Back to GitToken
                </Link>
              </main>
            }
          />
        </Routes>
        <footer className="mx-auto mt-12 max-w-3xl px-6 py-8 text-center text-night/60 dark:text-white/60 text-sm">
          <p>
            Thank you to the open-source tools and coding agents behind every
            commit.
          </p>
        </footer>
      </div>
    </BrowserRouter>
  );
}
