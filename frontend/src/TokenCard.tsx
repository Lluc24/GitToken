import type { Ref } from "react";
import { agentMarks } from "./agentMarks";
import type { Rarity } from "./api";
import { formatTokens } from "./format";

const maxAgentRows = 4;

type RarityStyle = {
  blobClassNames: [string, string, string];
  barClassName: string;
  accentTextClassName: string;
  glowClassName: string;
  rimClassName: string;
};

const styleByRarity: Record<Rarity, RarityStyle> = {
  common: {
    blobClassNames: ["bg-blue-400", "bg-sky-300", "bg-indigo-300"],
    barClassName: "from-blue-400 to-sky-300",
    accentTextClassName: "text-sky-200",
    glowClassName: "drop-shadow-[0_20px_50px_rgba(125,170,255,0.35)]",
    rimClassName: "glass-rim",
  },
  rare: {
    blobClassNames: ["bg-orange-400", "bg-rose-500", "bg-amber-300"],
    barClassName: "from-orange-400 to-rose-400",
    accentTextClassName: "text-orange-200",
    glowClassName: "drop-shadow-[0_20px_50px_rgba(255,140,80,0.4)]",
    rimClassName: "glass-rim",
  },
  epic: {
    blobClassNames: ["bg-violet-500", "bg-blue-500", "bg-fuchsia-400"],
    barClassName: "from-violet-400 to-blue-400",
    accentTextClassName: "text-violet-200",
    glowClassName: "drop-shadow-[0_20px_50px_rgba(178,107,255,0.45)]",
    rimClassName: "glass-rim",
  },
  legendary: {
    blobClassNames: ["bg-cyan-400", "bg-fuchsia-400", "bg-amber-300"],
    barClassName: "from-cyan-300 via-fuchsia-400 to-amber-300",
    accentTextClassName: "text-cyan-100",
    glowClassName: "drop-shadow-[0_20px_60px_rgba(103,232,249,0.5)]",
    rimClassName: "glass-rim-iridescent",
  },
  champion: {
    blobClassNames: ["bg-amber-400", "bg-orange-500", "bg-yellow-200"],
    barClassName: "from-amber-300 to-orange-400",
    accentTextClassName: "text-amber-100",
    glowClassName: "drop-shadow-[0_20px_60px_rgba(245,197,66,0.55)]",
    rimClassName: "glass-rim-iridescent",
  },
};

type TokenCardProps = {
  login: string;
  totalTokens: number;
  rarity: Rarity;
  tokensByAgent: Record<string, number>;
  nameByAgent: Record<string, string>;
  ref: Ref<HTMLElement>;
};

export function TokenCard({
  login,
  totalTokens,
  rarity,
  tokensByAgent,
  nameByAgent,
  ref,
}: TokenCardProps) {
  const style = styleByRarity[rarity];
  const agents = Object.entries(tokensByAgent).sort(
    (left, right) => right[1] - left[1],
  );
  const agentTotal = agents.reduce((sum, [, tokens]) => sum + tokens, 0);
  const hiddenAgentCount = agents.length - maxAgentRows;
  return (
    <article
      ref={ref}
      aria-label={`${login}: ${formatTokens(totalTokens)} tokens, ${rarity}`}
      className={`relative h-[520px] w-[300px] shrink-0 ${style.glowClassName}`}
    >
      <div className="absolute inset-0 overflow-hidden rounded-[36px] bg-night">
        <div
          className={`absolute -top-16 -left-16 size-56 rounded-full opacity-80 blur-3xl ${style.blobClassNames[0]}`}
        />
        <div
          className={`absolute top-1/3 -right-20 size-56 rounded-full opacity-70 blur-3xl ${style.blobClassNames[1]}`}
        />
        <div
          className={`absolute -bottom-20 left-10 size-52 rounded-full opacity-60 blur-3xl ${style.blobClassNames[2]}`}
        />
      </div>
      <div className="absolute inset-0 flex flex-col gap-2.5 rounded-[36px] p-2.5">
        <div className="relative h-[236px] shrink-0 overflow-hidden rounded-[28px] shadow-[inset_0_1px_0_rgb(255_255_255/0.5)]">
          <img
            src={`https://avatars.githubusercontent.com/${login}?size=400`}
            alt=""
            crossOrigin="anonymous"
            className="h-full w-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-white/15 via-transparent to-night/70" />
          <div className="glass absolute top-3 left-3 rounded-full px-3 py-1 font-bold text-sm text-white">
            {formatTokens(totalTokens)}
          </div>
          <div className="glass absolute inset-x-3 bottom-3 rounded-[20px] px-4 py-2 text-center">
            <p className="truncate font-bold text-2xl text-white tracking-tight">
              {login}
            </p>
            <p
              className={`font-semibold text-[11px] uppercase tracking-[0.3em] ${style.accentTextClassName}`}
            >
              {rarity}
            </p>
          </div>
        </div>
        <section
          aria-label="Estimated tokens by agent"
          className="glass flex-1 rounded-[28px] px-5 pt-4 pb-3"
        >
          <h2
            className={`font-semibold text-[11px] uppercase tracking-[0.25em] ${style.accentTextClassName}`}
          >
            Tokens by agent
          </h2>
          {agentTotal === 0 ? (
            <p className="mt-3 text-muted text-sm">
              No attributed agent tokens found.
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {agents.slice(0, maxAgentRows).map(([agent, tokens]) => (
                <li key={agent}>
                  <div className="mb-1 flex justify-between gap-3 text-sm">
                    <span className="flex items-center gap-2 font-medium">
                      {agentMarks[agent] ? (
                        <svg
                          viewBox="0 0 24 24"
                          className="h-4 w-4 fill-current"
                          aria-hidden="true"
                        >
                          <path d={agentMarks[agent]} />
                        </svg>
                      ) : null}
                      {nameByAgent[agent] ?? agent}
                    </span>
                    <span className="font-mono text-xs leading-5">
                      {formatTokens(tokens)}{" "}
                      <span className="text-muted">
                        {Math.round((tokens / agentTotal) * 100)}%
                      </span>
                    </span>
                  </div>
                  <div
                    className="h-1.5 overflow-hidden rounded-full bg-white/10"
                    aria-hidden="true"
                  >
                    <div
                      className={`h-full rounded-full bg-gradient-to-r shadow-[0_0_10px_rgb(255_255_255/0.4)] ${style.barClassName}`}
                      style={{ width: `${(tokens / agentTotal) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
          {hiddenAgentCount > 0 && (
            <p className="mt-2 text-muted text-xs">
              +{hiddenAgentCount} more agents
            </p>
          )}
        </section>
        <p className="text-center font-semibold text-[10px] text-white/50 tracking-[0.35em]">
          GITTOKEN
        </p>
      </div>
      <div
        className={`pointer-events-none absolute inset-0 rounded-[36px] ${style.rimClassName}`}
      />
    </article>
  );
}
