import { Link } from "react-router-dom";
import { useLeaderboard } from "./api";
import { formatTokens } from "./format";
import { glassClassName } from "./glass";

const medalClassNames = [
  "bg-gradient-to-br from-amber-200 to-amber-500 text-night",
  "bg-gradient-to-br from-slate-100 to-slate-400 text-night",
  "bg-gradient-to-br from-orange-300 to-orange-700 text-night",
];

export function Leaderboard() {
  const result = useLeaderboard();
  return (
    <section className={`w-full rounded-[32px] p-6 ${glassClassName}`}>
      <h1 className="font-bold text-3xl tracking-tight">Leaderboard</h1>
      <p className="mt-2 text-muted text-sm">
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
        <p className="mt-4 text-muted">
          No recent profiles yet. Estimate a profile to get started.
        </p>
      ) : (
        <ol className="mt-4 space-y-1.5">
          {result.data.map((profile, index) => (
            <li
              key={profile.login}
              className="flex items-center gap-3 rounded-2xl px-3 py-2.5 transition-colors hover:bg-ink/10"
            >
              <span
                className={`flex size-7 items-center justify-center rounded-full font-semibold text-xs ${medalClassNames[index] ?? "text-muted"}`}
              >
                {index + 1}
              </span>
              <img
                src={`https://avatars.githubusercontent.com/${encodeURIComponent(profile.login)}?size=64`}
                alt=""
                className="size-8 rounded-full ring-1 ring-ink/30"
              />
              <Link
                to={`/${encodeURIComponent(profile.login)}`}
                className="min-w-0 flex-1 truncate font-medium hover:text-link"
              >
                {profile.login}
              </Link>
              <span className="font-mono text-sm">
                {formatTokens(profile.total_tokens)}
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
