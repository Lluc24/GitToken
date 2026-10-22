import type { Ref } from "react";
import { agentMarks } from "./agentMarks";
import type { Rarity } from "./api";
import { formatTokens } from "./format";

const maxAgentRows = 2;

type RarityStyle = {
  tintClassName: string;
  barClassName: string;
  accentTextClassName: string;
  rimClassName: string;
};

const styleByRarity: Record<Rarity, RarityStyle> = {
  common: {
    tintClassName: "from-sky-400/20",
    barClassName: "from-blue-400 to-sky-300",
    accentTextClassName: "text-sky-300",
    rimClassName:
      "glass-rim bg-gradient-to-br from-sky-200 via-sky-400/40 to-blue-500",
  },
  rare: {
    tintClassName: "from-orange-400/20",
    barClassName: "from-orange-400 to-rose-400",
    accentTextClassName: "text-orange-300",
    rimClassName:
      "glass-rim bg-gradient-to-br from-amber-200 via-orange-400/40 to-rose-500",
  },
  epic: {
    tintClassName: "from-violet-500/25",
    barClassName: "from-violet-400 to-blue-400",
    accentTextClassName: "text-violet-300",
    rimClassName:
      "glass-rim bg-gradient-to-br from-fuchsia-300 via-violet-500/40 to-blue-500",
  },
  legendary: {
    tintClassName: "from-cyan-400/20",
    barClassName: "from-cyan-300 via-fuchsia-400 to-amber-300",
    accentTextClassName: "text-cyan-200",
    rimClassName: "glass-rim-iridescent",
  },
  champion: {
    tintClassName: "from-amber-400/25",
    barClassName: "from-amber-300 to-orange-400",
    accentTextClassName: "text-amber-300",
    rimClassName: "glass-rim-iridescent",
  },
};

type AgentRow = { key: string; name: string; tokens: number };

// Up to two agents are shown by name; beyond that, the top agent plus everyone else folded into "Others".
function agentRows(
  tokensByAgent: Record<string, number>,
  nameByAgent: Record<string, string>,
): AgentRow[] {
  const rows = Object.entries(tokensByAgent)
    .sort((left, right) => right[1] - left[1])
    .map(([agent, tokens]) => ({
      key: agent,
      name: nameByAgent[agent] ?? agent,
      tokens,
    }));
  if (rows.length > maxAgentRows) {
    const othersTokens = rows
      .slice(1)
      .reduce((sum, row) => sum + row.tokens, 0);
    return [
      ...rows.slice(0, 1),
      { key: "others", name: "Others", tokens: othersTokens },
    ];
  }
  return rows;
}

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
  const rows = agentRows(tokensByAgent, nameByAgent);
  const agentTotal = rows.reduce((sum, row) => sum + row.tokens, 0);
  return (
    <article
      ref={ref}
      aria-label={`${login}: ${formatTokens(totalTokens)} tokens, ${rarity}`}
      className="relative w-[300px] shrink-0 overflow-hidden rounded-[36px] bg-[#0b0e1a] shadow-[0_30px_80px_-30px_rgb(0_0_0/0.9)]"
    >
      <div
        className={`absolute inset-0 bg-gradient-to-b to-transparent to-60% ${style.tintClassName}`}
      />
      <div className="relative flex flex-col gap-3 p-2.5 pb-3">
        <img
          src={`https://avatars.githubusercontent.com/${login}?size=400`}
          alt=""
          crossOrigin="anonymous"
          className="aspect-square w-full rounded-[28px] object-cover shadow-[inset_0_1px_0_rgb(255_255_255/0.5)]"
        />
        <div className="flex items-end justify-between gap-3 px-2.5">
          <div className="min-w-0">
            <p className="truncate font-bold text-2xl text-white tracking-tight">
              {login}
            </p>
            <p
              className={`font-semibold text-[11px] uppercase tracking-[0.3em] ${style.accentTextClassName}`}
            >
              {rarity}
            </p>
          </div>
          <p
            className={`shrink-0 font-bold text-3xl tracking-tight ${style.accentTextClassName}`}
          >
            {formatTokens(totalTokens)}
          </p>
        </div>
        {agentTotal > 0 && (
          <ul
            aria-label="Estimated tokens by agent"
            className="space-y-2.5 rounded-[24px] bg-white/[0.06] px-4 py-3.5 shadow-[inset_0_1px_0_rgb(255_255_255/0.12)]"
          >
            {rows.map((row) => (
              <li key={row.key}>
                <div className="mb-1 flex justify-between gap-3 text-sm">
                  <span className="flex items-center gap-2 font-medium">
                    {agentMarks[row.key] ? (
                      <svg
                        viewBox="0 0 24 24"
                        className="h-4 w-4 fill-current"
                        aria-hidden="true"
                      >
                        <path d={agentMarks[row.key]} />
                      </svg>
                    ) : null}
                    {row.name}
                  </span>
                  <span className="font-mono text-xs leading-5">
                    {formatTokens(row.tokens)}{" "}
                    <span className="text-muted">
                      {Math.round((row.tokens / agentTotal) * 100)}%
                    </span>
                  </span>
                </div>
                <div
                  className="h-1.5 overflow-hidden rounded-full bg-white/10"
                  aria-hidden="true"
                >
                  <div
                    className={`h-full rounded-full bg-gradient-to-r ${style.barClassName}`}
                    style={{ width: `${(row.tokens / agentTotal) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
        <p className="text-center font-semibold text-[10px] text-white/40 tracking-[0.35em]">
          GITTOKEN
        </p>
      </div>
      <div
        className={`pointer-events-none absolute inset-0 rounded-[36px] ${style.rimClassName}`}
      />
    </article>
  );
}
