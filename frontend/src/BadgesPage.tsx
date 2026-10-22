import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { type Badge, badges } from "./badges";
import { glassClassName, pressableClassName } from "./glass";
import { LoginForm } from "./LoginForm";

type Background = "light" | "dark";
type SnippetFormat = "Markdown" | "HTML" | "URL";

const snippetFormats: SnippetFormat[] = ["Markdown", "HTML", "URL"];

const previewClassNameByBackground: Record<Background, string> = {
  light: "bg-white shadow-[inset_0_0_0_1px_rgb(0_0_0/0.06)]",
  dark: "bg-[#0d1117] shadow-[inset_0_0_0_1px_rgb(255_255_255/0.08)]",
};

function snippet(
  format: SnippetFormat,
  login: string,
  badge: Badge,
  origin: string,
): string {
  const badgeUrl = `${origin}${badge.path(login)}`;
  const profileUrl = `${origin}/${encodeURIComponent(login)}`;
  const alt = `${login}'s GitToken ${badge.name.toLowerCase()}`;
  const snippetByFormat: Record<SnippetFormat, string> = {
    Markdown: `[![${alt}](${badgeUrl})](${profileUrl})`,
    HTML: `<a href="${profileUrl}"><img src="${badgeUrl}" alt="${alt}"></a>`,
    URL: badgeUrl,
  };
  return snippetByFormat[format];
}

type SegmentedControlProps<Option extends string> = {
  label: string;
  options: Option[];
  selected: Option;
  onSelect: (option: Option) => void;
};

function SegmentedControl<Option extends string>({
  label,
  options,
  selected,
  onSelect,
}: SegmentedControlProps<Option>) {
  return (
    <fieldset className="flex w-fit rounded-full bg-white/10 p-1 text-sm">
      <legend className="sr-only">{label}</legend>
      {options.map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={option === selected}
          onClick={() => onSelect(option)}
          className={`rounded-full px-3 py-1 capitalize transition-colors ${option === selected ? "bg-white font-medium text-night" : "text-white/70 hover:text-white"}`}
        >
          {option}
        </button>
      ))}
    </fieldset>
  );
}

function BadgeSection({ login, badge }: { login: string; badge: Badge }) {
  const [background, setBackground] = useState<Background>("light");
  const [format, setFormat] = useState<SnippetFormat>("Markdown");
  const [copiedFormat, setCopiedFormat] = useState<SnippetFormat | null>(null);
  const text = snippet(format, login, badge, window.location.origin);

  async function copySnippet() {
    await navigator.clipboard.writeText(text);
    setCopiedFormat(format);
  }

  return (
    <section
      aria-labelledby={`badge-${badge.name}`}
      className={`rounded-[32px] p-5 ${glassClassName}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 px-1">
        <div>
          <h2
            id={`badge-${badge.name}`}
            className="font-semibold text-xl tracking-tight"
          >
            {badge.name}
          </h2>
          <p className="text-muted text-sm">{badge.description}</p>
        </div>
        <SegmentedControl
          label="Preview background"
          options={["light", "dark"]}
          selected={background}
          onSelect={setBackground}
        />
      </div>
      <div
        className={`mt-4 flex justify-center rounded-3xl p-8 ${previewClassNameByBackground[background]}`}
      >
        <img src={badge.path(login)} alt={`${login}'s ${badge.name} badge`} />
      </div>
      <div className="mt-4">
        <SegmentedControl
          label="Snippet format"
          options={snippetFormats}
          selected={format}
          onSelect={setFormat}
        />
      </div>
      <div className="mt-2 flex items-center gap-2 rounded-2xl bg-black/40 py-2 pr-2 pl-4 shadow-[inset_0_1px_0_rgb(255_255_255/0.08)]">
        <code className="min-w-0 flex-1 truncate font-mono text-[13px] text-white/85">
          {text}
        </code>
        <button
          type="button"
          onClick={copySnippet}
          className={`shrink-0 rounded-full bg-gradient-to-br from-cyan-300 via-violet-400 to-fuchsia-400 px-4 py-1.5 font-semibold text-night text-sm ${pressableClassName}`}
        >
          {copiedFormat === format ? "Copied ✓" : "Copy"}
        </button>
      </div>
      <p role="status" className="sr-only">
        {copiedFormat === format ? `${format} snippet copied` : ""}
      </p>
    </section>
  );
}

export function BadgesPage() {
  const { login = "" } = useParams();
  const navigate = useNavigate();

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-bold text-4xl tracking-tight">Badges</h1>
          <p className="mt-1 text-muted">
            Embed your GitToken in a README or a website. They update every day.
          </p>
        </div>
        {login !== "" && (
          <div
            className={`flex items-center gap-2 rounded-full p-1 ${glassClassName}`}
          >
            <img
              src={`https://avatars.githubusercontent.com/${encodeURIComponent(login)}?size=64`}
              alt=""
              className="size-8 rounded-full ring-1 ring-white/30"
            />
            <span className="font-medium">{login}</span>
            <Link
              to="/badges"
              className="rounded-full bg-white/10 px-3 py-1.5 text-sm text-white/80 hover:bg-white/20 hover:text-white"
            >
              Change
            </Link>
          </div>
        )}
      </div>
      {login === "" ? (
        <LoginForm
          initialLogin=""
          submitLabel="Show badges"
          onSubmitLogin={(typedLogin) =>
            navigate(
              typedLogin === ""
                ? "/badges"
                : `/${encodeURIComponent(typedLogin)}/badges`,
            )
          }
        />
      ) : (
        badges.map((badge) => (
          <BadgeSection key={badge.name} login={login} badge={badge} />
        ))
      )}
    </main>
  );
}
