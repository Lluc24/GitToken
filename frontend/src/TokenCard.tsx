import type { Rarity } from "./api";
import { formatTokens } from "./format";

// Legendary and champion cards have cut corners in Clash Royale; the lower rarities are rounded.
function cutCornersOutline(cutPixels: number): string {
  return `polygon(${cutPixels}px 0, calc(100% - ${cutPixels}px) 0, 100% ${cutPixels}px, 100% calc(100% - ${cutPixels}px), calc(100% - ${cutPixels}px) 100%, ${cutPixels}px 100%, 0 calc(100% - ${cutPixels}px), 0 ${cutPixels}px)`;
}

type RarityStyle = {
  frameClassName: string;
  accentTextClassName: string;
  accentBorderClassName: string;
  glowClassName: string;
  hasCutCorners: boolean;
};

const styleByRarity: Record<Rarity, RarityStyle> = {
  common: {
    frameClassName: "from-card-common to-card-common-dark",
    accentTextClassName: "text-card-common",
    accentBorderClassName: "border-card-common",
    glowClassName: "drop-shadow-[0_0_40px_rgba(228,233,239,0.2)]",
    hasCutCorners: false,
  },
  rare: {
    frameClassName: "from-card-rare to-card-rare-dark",
    accentTextClassName: "text-card-rare",
    accentBorderClassName: "border-card-rare",
    glowClassName: "drop-shadow-[0_0_40px_rgba(255,177,94,0.3)]",
    hasCutCorners: false,
  },
  epic: {
    frameClassName: "from-card-epic to-card-epic-dark",
    accentTextClassName: "text-card-epic",
    accentBorderClassName: "border-card-epic",
    glowClassName: "drop-shadow-[0_0_40px_rgba(214,140,255,0.35)]",
    hasCutCorners: false,
  },
  legendary: {
    frameClassName: "from-cyan-300 via-fuchsia-400 to-amber-300",
    accentTextClassName: "text-cyan-200",
    accentBorderClassName: "border-cyan-200",
    glowClassName: "drop-shadow-[0_0_40px_rgba(103,232,249,0.4)]",
    hasCutCorners: true,
  },
  champion: {
    frameClassName: "from-card-gold to-card-gold-dark",
    accentTextClassName: "text-card-gold",
    accentBorderClassName: "border-card-gold",
    glowClassName: "drop-shadow-[0_0_48px_rgba(230,198,92,0.5)]",
    hasCutCorners: true,
  },
};

type TokenCardProps = {
  login: string;
  totalTokens: number;
  rarity: Rarity;
};

export function TokenCard({ login, totalTokens, rarity }: TokenCardProps) {
  const style = styleByRarity[rarity];
  const badgePositionClassName = style.hasCutCorners
    ? "top-9 left-7"
    : "top-6 left-4";
  return (
    <article
      aria-label={`${login}: ${formatTokens(totalTokens)} tokens, ${rarity}`}
      className={`relative h-[400px] w-[300px] shrink-0 ${style.glowClassName}`}
    >
      <div
        className={`absolute inset-0 rounded-2xl bg-gradient-to-b ring-2 ring-black/60 ${style.frameClassName}`}
        style={{
          clipPath: style.hasCutCorners ? cutCornersOutline(32) : undefined,
        }}
      />
      <div
        className="absolute inset-[5px] overflow-hidden rounded-xl bg-gradient-to-b from-pitch-blue to-pitch-night"
        style={{
          clipPath: style.hasCutCorners ? cutCornersOutline(30) : undefined,
        }}
      >
        <img
          src={`https://github.com/${login}.png?size=400`}
          alt=""
          className="h-[300px] w-full object-cover"
        />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-pitch-night to-transparent" />
      </div>
      <div
        className={`absolute flex size-[64px] -rotate-45 items-center justify-center rounded-[50%_0_50%_50%] border-2 bg-pitch-night shadow-lg ${style.accentBorderClassName} ${badgePositionClassName}`}
      >
        <span
          className={`rotate-45 font-bold font-display text-sm ${style.accentTextClassName}`}
        >
          {formatTokens(totalTokens)}
        </span>
      </div>
      <div
        className={`absolute inset-x-6 bottom-5 border-y bg-pitch-night/80 py-1 text-center font-display uppercase ${style.accentBorderClassName}`}
      >
        <p className="truncate font-bold text-3xl text-white tracking-wide">
          {login}
        </p>
        <p className={`text-xs tracking-[0.3em] ${style.accentTextClassName}`}>
          {rarity}
        </p>
      </div>
    </article>
  );
}
