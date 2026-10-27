import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { type Badge, badges } from "./badges";
import { glassClassName, pressableClassName } from "./glass";
import { LoginForm } from "./LoginForm";
import { type Theme, useTheme } from "./theme";

type SnippetFormat = "README" | "Markdown" | "URL";

const snippetFormats: SnippetFormat[] = ["README", "Markdown", "URL"];

// README follows the reader's GitHub theme through <picture>; the others use the site's theme.
function snippet(
  format: SnippetFormat,
  login: string,
  badge: Badge,
  theme: Theme,
): string {
  const { origin } = window.location;
  const badgeUrl = `${origin}${badge.path(login, theme)}`;
  const profileUrl = `${origin}/${encodeURIComponent(login)}`;
  const alt = `${login}'s GitToken ${badge.name.toLowerCase()}`;
  const snippetByFormat: Record<SnippetFormat, string> = {
    README: [
      `<a href="${profileUrl}">`,
      "  <picture>",
      `    <source media="(prefers-color-scheme: dark)" srcset="${origin}${badge.path(login, "dark")}">`,
      `    <img src="${origin}${badge.path(login, "light")}" alt="${alt}">`,
      "  </picture>",
      "</a>",
    ].join("\n"),
    Markdown: `[![${alt}](${badgeUrl})](${profileUrl})`,
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
    <fieldset className="flex w-fit rounded-full bg-night/10 dark:bg-white/10 p-1 text-sm">
      <legend className="sr-only">{label}</legend>
      {options.map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={option === selected}
          onClick={() => onSelect(option)}
          className={`rounded-full px-3 py-1 transition-colors ${option === selected ? "bg-night dark:bg-white font-medium text-white dark:text-night" : "text-night/70 dark:text-white/70 hover:text-night dark:hover:text-white"}`}
        >
          {option}
        </button>
      ))}
    </fieldset>
  );
}

function BadgeSection({ login, badge }: { login: string; badge: Badge }) {
  const theme = useTheme();
  const [format, setFormat] = useState<SnippetFormat>("README");
  const [copiedFormat, setCopiedFormat] = useState<SnippetFormat | null>(null);
  const text = snippet(format, login, badge, theme);

  async function copySnippet() {
    await navigator.clipboard.writeText(text);
    setCopiedFormat(format);
  }

  return (
    <section
      aria-labelledby={`badge-${badge.name}`}
      className={`rounded-[32px] p-5 ${glassClassName}`}
    >
      <div className="px-1">
        <h2
          id={`badge-${badge.name}`}
          className="font-semibold text-xl tracking-tight"
        >
          {badge.name}
        </h2>
        <p className="text-night/60 dark:text-white/60 text-sm">
          {badge.description}
        </p>
      </div>
      <div className="flex justify-center py-6">
        <img
          src={badge.path(login, theme)}
          alt={`${login}'s ${badge.name} badge`}
        />
      </div>
      <div className="mt-4">
        <SegmentedControl
          label="Snippet format"
          options={snippetFormats}
          selected={format}
          onSelect={setFormat}
        />
      </div>
      <div className="mt-2 flex items-center gap-2 rounded-2xl bg-night/5 dark:bg-black/40 py-2 pr-2 pl-4 shadow-[inset_0_1px_0_rgb(255_255_255/0.08)]">
        <code className="min-w-0 flex-1 truncate font-mono text-[13px] text-night/85 dark:text-white/85">
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

export function BadgesPage({
  onViewLogin,
}: {
  onViewLogin: (login: string) => void;
}) {
  const { login = "" } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    if (login !== "") {
      onViewLogin(login);
    }
  }, [onViewLogin, login]);

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-bold text-4xl tracking-tight">Badges</h1>
          <p className="mt-1 text-night/60 dark:text-white/60">
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
              className="size-8 rounded-full ring-1 ring-night/30 dark:ring-white/30"
            />
            <span className="font-medium">{login}</span>
            <Link
              to="/badges"
              className="rounded-full bg-night/10 dark:bg-white/10 px-3 py-1.5 text-sm text-night/80 dark:text-white/80 hover:bg-night/20 dark:hover:bg-white/20 hover:text-night dark:hover:text-white"
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
