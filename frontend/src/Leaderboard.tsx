import { Link } from "react-router-dom";
import { type Rarity, useLeaderboard } from "./api";
import { formatTokens } from "./format";
import { glassClassName } from "./glass";

const medalClassNames = [
  "bg-gradient-to-br from-amber-200 to-amber-500 text-night",
  "bg-gradient-to-br from-slate-100 to-slate-400 text-night",
  "bg-gradient-to-br from-orange-300 to-orange-700 text-night",
];

const rarityClassNames: Record<Rarity, string> = {
  common: "text-sky-600 dark:text-sky-300",
  rare: "text-orange-600 dark:text-orange-300",
  epic: "text-violet-600 dark:text-violet-300",
  legendary: "text-cyan-600 dark:text-cyan-300",
  champion: "text-amber-600 dark:text-amber-300",
};

export function Leaderboard() {
  const result = useLeaderboard();
  return (
    <section className={`w-full rounded-[32px] p-4 sm:p-6 ${glassClassName}`}>
      <h1 className="font-bold text-3xl tracking-tight">Leaderboard</h1>
      <p className="mt-2 text-night/60 dark:text-white/60 text-sm">
        Profiles scanned in the last day. Estimated tokens, not a global
        ranking.
      </p>
      {result.isPending ? (
        <p className="mt-4">Loading profiles...</p>
      ) : result.isError ? (
        <p className="mt-4" role="alert">
          {result.error.message}
        </p>
      ) : result.data.length === 0 ? (
        <p className="mt-4 text-night/60 dark:text-white/60">
          No recent profiles yet. Estimate a profile to get started.
        </p>
      ) : (
        <ol className="mt-4 space-y-1.5">
          {result.data.map((profile, index) => (
            <li
              key={profile.login}
              className="relative flex items-center gap-2.5 rounded-2xl px-2 py-2.5 transition-colors sm:gap-3 sm:px-3 hover:bg-night/10 dark:hover:bg-white/10"
            >
              <span
                className={`flex size-7 items-center justify-center rounded-full font-semibold text-xs ${medalClassNames[index] ?? "text-night/60 dark:text-white/60"}`}
              >
                {index + 1}
              </span>
              <img
                src={`https://avatars.githubusercontent.com/${encodeURIComponent(profile.login)}?size=64`}
                alt=""
                className="size-8 rounded-full ring-1 ring-night/30 dark:ring-white/30"
              />
              <div className="min-w-0 flex-1 sm:flex sm:items-center sm:gap-3">
                <Link
                  to={`/${encodeURIComponent(profile.login)}`}
                  className="block truncate font-medium after:absolute after:inset-0 after:rounded-2xl hover:text-cyan-700 sm:flex-1 dark:hover:text-cyan-200"
                >
                  {profile.login}
                </Link>
                <span
                  className={`block font-medium text-xs ${rarityClassNames[profile.rarity]}`}
                >
                  {profile.rarity}
                </span>
              </div>
              <span className="shrink-0 font-mono text-sm tabular-nums sm:min-w-16 sm:text-right">
                {formatTokens(profile.totalTokens)}
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
