import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { type Badge, badges } from "./badges";
import { ErrorNotice } from "./ErrorNotice";
import { glassClassName, primaryActionClassName } from "./glass";
import { LoginForm } from "./LoginForm";
import {
  type GithubLogin,
  invalidLoginMessage,
  parseRouteLogin,
} from "./login";
import {
  avatarUrl,
  badgesIndexPath,
  badgesPagePath,
  profilePath,
} from "./paths";
import { SegmentedControl } from "./SegmentedControl";
import { type Theme, useTheme } from "./theme";

const snippetFormats = ["README", "Markdown", "URL"] as const;

type SnippetFormat = (typeof snippetFormats)[number];

const copiedLabelDurationMilliseconds = 2000;

type CopyResult = "copied" | "failed";

// README follows the reader's GitHub theme through <picture>; the others use the site's theme.
function snippet(
  format: SnippetFormat,
  login: GithubLogin,
  badge: Badge,
  theme: Theme,
): string {
  const { origin } = window.location;
  const badgeUrl = `${origin}${badge.path(login, theme)}`;
  const profileUrl = `${origin}${profilePath(login)}`;
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

function BadgeSection({ login, badge }: { login: GithubLogin; badge: Badge }) {
  const theme = useTheme();
  const [format, setFormat] = useState<SnippetFormat>("README");
  const [copyResult, setCopyResult] = useState<CopyResult | null>(null);
  const text = snippet(format, login, badge, theme);
  const isCopied = copyResult === "copied";

  useEffect(() => {
    if (isCopied) {
      const timeoutId = setTimeout(
        () => setCopyResult(null),
        copiedLabelDurationMilliseconds,
      );
      return () => clearTimeout(timeoutId);
    }
    return undefined;
  }, [isCopied]);

  function selectFormat(selectedFormat: SnippetFormat) {
    setFormat(selectedFormat);
    setCopyResult(null);
  }

  async function copySnippet() {
    setCopyResult(null);
    try {
      await navigator.clipboard.writeText(text);
      setCopyResult("copied");
    } catch {
      setCopyResult("failed");
    }
  }

  return (
    <section
      aria-labelledby={`badge-${badge.name}`}
      className={`rounded-[32px] p-4 sm:p-5 ${glassClassName}`}
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
          variant="text"
          options={snippetFormats}
          selected={format}
          onSelect={selectFormat}
          renderOption={(option) => option}
        />
      </div>
      <div className="mt-2 flex items-center gap-2 rounded-2xl bg-night/5 dark:bg-black/40 py-2 pr-2 pl-4 shadow-[inset_0_1px_0_rgb(255_255_255/0.08)]">
        <code className="min-w-0 flex-1 truncate font-mono text-[13px] text-night/85 dark:text-white/85">
          {text}
        </code>
        <button
          type="button"
          onClick={copySnippet}
          className={`shrink-0 px-4 py-2 text-sm sm:py-1.5 ${primaryActionClassName}`}
        >
          {isCopied ? "Copied ✓" : "Copy"}
        </button>
      </div>
      <p role="status" className="sr-only">
        {isCopied ? `${format} snippet copied` : ""}
      </p>
      {copyResult === "failed" && (
        <p
          role="alert"
          className="mt-2 px-1 text-rose-700 text-sm dark:text-rose-200"
        >
          Couldn't copy. Select the snippet and copy it yourself.
        </p>
      )}
    </section>
  );
}

export function BadgesPage({
  onViewLogin,
}: {
  onViewLogin: (login: GithubLogin) => void;
}) {
  const { login: routeLogin } = useParams();
  const login = parseRouteLogin(routeLogin);
  const navigate = useNavigate();

  useEffect(() => {
    if (login !== null) {
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
        {login !== null && (
          <div
            className={`flex max-w-full items-center gap-2 rounded-full p-1 ${glassClassName}`}
          >
            <img
              src={avatarUrl(login)}
              alt=""
              className="size-8 shrink-0 rounded-full ring-1 ring-night/30 dark:ring-white/30"
            />
            <span className="min-w-0 truncate font-medium">{login}</span>
            <Link
              to={badgesIndexPath}
              className="shrink-0 rounded-full bg-night/10 dark:bg-white/10 px-3 py-2 text-sm sm:py-1.5 text-night/80 dark:text-white/80 hover:bg-night/20 dark:hover:bg-white/20 hover:text-night dark:hover:text-white"
            >
              Change
            </Link>
          </div>
        )}
      </div>
      {routeLogin !== undefined && login === null && (
        <ErrorNotice message={invalidLoginMessage(routeLogin)} />
      )}
      {login === null ? (
        <LoginForm
          initialLogin=""
          submitLabel="Show badges"
          onSubmitLogin={(typedLogin) => navigate(badgesPagePath(typedLogin))}
        />
      ) : (
        badges.map((badge) => (
          <BadgeSection key={badge.name} login={login} badge={badge} />
        ))
      )}
    </main>
  );
}
