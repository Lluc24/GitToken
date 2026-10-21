import { useLeaderboard } from "./api";
import { formatTokens } from "./format";

export function Leaderboard() {
  const result = useLeaderboard();
  return (
    <section className="w-full rounded-2xl border border-white/10 bg-pitch-night/50 p-5">
      <h1 className="font-display text-2xl uppercase">Leaderboard</h1>
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
        <ol className="mt-4 divide-y divide-white/10">
          {result.data.map((profile, index) => (
            <li key={profile.login} className="flex items-center gap-3 py-3">
              <span className="w-6 text-muted">{index + 1}</span>
              <a
                href={`https://github.com/${encodeURIComponent(profile.login)}`}
                className="min-w-0 flex-1 truncate hover:text-scout-green"
              >
                {profile.login}
              </a>
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
