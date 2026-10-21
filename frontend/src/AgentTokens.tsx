import { formatTokens } from "./format";

export function AgentTokens({
  tokensByAgent,
  nameByAgent,
}: {
  tokensByAgent: Record<string, number>;
  nameByAgent: Record<string, string>;
}) {
  const agents = Object.entries(tokensByAgent).sort(
    (left, right) => right[1] - left[1],
  );
  const total = agents.reduce((sum, [, tokens]) => sum + tokens, 0);
  return (
    <section
      className="w-full rounded-2xl border border-white/10 bg-pitch-night/50 p-5"
      aria-label="Estimated tokens by agent"
    >
      <h2 className="font-display text-xl uppercase tracking-wide">
        Tokens by agent
      </h2>
      {total === 0 ? (
        <p className="mt-3 text-muted">No attributed agent tokens found.</p>
      ) : (
        <ul className="mt-4 space-y-4">
          {agents.map(([agent, tokens]) => (
            <li key={agent}>
              <div className="mb-1 flex justify-between gap-3 text-sm">
                <span>{nameByAgent[agent] ?? agent}</span>
                <span className="font-mono">
                  {formatTokens(tokens)}{" "}
                  <span className="text-muted">
                    ({Math.round((tokens / total) * 100)}%)
                  </span>
                </span>
              </div>
              <div
                className="h-2 overflow-hidden rounded-full bg-white/10"
                aria-hidden="true"
              >
                <div
                  className="h-full rounded-full bg-scout-green"
                  style={{ width: `${(tokens / total) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
