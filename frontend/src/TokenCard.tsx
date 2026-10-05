import { formatTokens } from "./format";

type TokenCardProps = {
  login: string;
  totalTokens: number;
};

export function TokenCard({ login, totalTokens }: TokenCardProps) {
  return (
    <article
      aria-label={`${login}: ${formatTokens(totalTokens)} tokens`}
      className="relative h-[400px] w-[300px] shrink-0 drop-shadow-[0_0_40px_rgba(228,233,239,0.2)]"
    >
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-b from-card-common to-card-common-dark ring-2 ring-black/60" />
      <div className="absolute inset-[5px] overflow-hidden rounded-xl bg-gradient-to-b from-pitch-blue to-pitch-night">
        <img
          src={`https://github.com/${login}.png?size=400`}
          alt=""
          className="h-[300px] w-full object-cover"
        />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-pitch-night to-transparent" />
      </div>
      <div className="absolute top-6 left-4 flex size-[64px] -rotate-45 items-center justify-center rounded-[50%_0_50%_50%] border-2 border-card-common bg-pitch-night shadow-lg">
        <span className="rotate-45 font-bold font-display text-card-common text-sm">
          {formatTokens(totalTokens)}
        </span>
      </div>
      <div className="absolute inset-x-6 bottom-5 border-card-common border-y bg-pitch-night/80 py-1 text-center font-display uppercase">
        <p className="truncate font-bold text-3xl text-white tracking-wide">
          {login}
        </p>
        <p className="text-card-common text-xs tracking-[0.3em]">Common</p>
      </div>
    </article>
  );
}
