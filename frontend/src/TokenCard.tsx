import { formatTokens } from "./format";

// Clash Royale card silhouette: a rounded rectangle whose top edge arches up.
const outerOutline =
  "path('M0 48Q0 28 20 24Q150 -4 280 24Q300 28 300 48L300 376Q300 400 276 400L24 400Q0 400 0 376Z')";
const innerOutline =
  "path('M0 44Q0 25 19 21Q144 -4 269 21Q288 25 288 44L288 365Q288 388 265 388L23 388Q0 388 0 365Z')";

type TokenCardProps = {
  login: string;
  totalTokens: number;
};

export function TokenCard({ login, totalTokens }: TokenCardProps) {
  return (
    <article
      aria-label={`${login}: ${formatTokens(totalTokens)} tokens`}
      className="relative h-[400px] w-[300px] shrink-0 drop-shadow-[0_0_40px_rgba(230,198,92,0.25)]"
    >
      <div
        className="absolute inset-0 bg-gradient-to-b from-card-gold to-card-gold-dark"
        style={{ clipPath: outerOutline }}
      />
      <div
        className="absolute inset-[6px] overflow-hidden bg-gradient-to-b from-pitch-blue to-pitch-night"
        style={{ clipPath: innerOutline }}
      >
        <img
          src={`https://github.com/${login}.png?size=400`}
          alt=""
          className="h-[300px] w-full object-cover"
        />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-pitch-night to-transparent" />
      </div>
      <div className="absolute top-3 left-3 flex size-[72px] -rotate-45 items-center justify-center rounded-[50%_0_50%_50%] border-2 border-card-gold bg-pitch-night shadow-lg">
        <span className="rotate-45 font-bold font-display text-base text-card-gold">
          {formatTokens(totalTokens)}
        </span>
      </div>
      <p className="absolute inset-x-6 bottom-6 truncate border-card-gold border-y bg-pitch-night/80 py-1 text-center font-bold font-display text-3xl text-card-gold uppercase tracking-wide">
        {login}
      </p>
    </article>
  );
}
