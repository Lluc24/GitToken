import { Link } from "react-router-dom";
import {
  type Rarity,
  type RarityThreshold,
  useLeaderboard,
  useRarities,
} from "./api";
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

function rarityFor(totalTokens: number, thresholds: RarityThreshold[]): Rarity {
  let result: Rarity = "common";
  let bestMin = 0;
  for (const threshold of thresholds) {
    if (
      totalTokens >= threshold.min_tokens &&
      threshold.min_tokens >= bestMin
    ) {
      bestMin = threshold.min_tokens;
      result = threshold.rarity;
    }
  }
  return result;
}

export function Leaderboard() {
  const result = useLeaderboard();
  const rarities = useRarities();
  return (
    <section className={`w-full rounded-[32px] p-6 ${glassClassName}`}>
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
              className="flex items-center gap-3 rounded-2xl px-3 py-2.5 transition-colors hover:bg-night/10 dark:hover:bg-white/10"
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
              <Link
                to={`/${encodeURIComponent(profile.login)}`}
                className="min-w-0 flex-1 truncate font-medium hover:text-cyan-700 dark:hover:text-cyan-200"
              >
                {profile.login}
              </Link>
              {rarities.isSuccess && (
                <span
                  className={`font-medium text-xs ${rarityClassNames[rarityFor(profile.total_tokens, rarities.data)]}`}
                >
                  {rarityFor(profile.total_tokens, rarities.data)}
                </span>
              )}
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
