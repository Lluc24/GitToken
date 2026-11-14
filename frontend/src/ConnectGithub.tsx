import { Link, useSearchParams } from "react-router-dom";
import { useProfileTokens } from "./api";
import { readConnectedKey } from "./badges";
import { pressableClassName } from "./glass";
import { searchFocusPath } from "./paths";

const buttonClassName =
  "flex items-center gap-1.5 rounded-full px-3.5 py-2 font-semibold text-sm";
const enabledClassName = `${buttonClassName} bg-night text-white dark:bg-white dark:text-night ${pressableClassName}`;

type ConnectGithubProps = { login: string; onNavigate: () => void };

function GithubMark() {
  return (
    <svg
      viewBox="0 0 16 16"
      className="size-4 shrink-0 max-[359px]:hidden"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z" />
    </svg>
  );
}

function SearchFirstLink({ onNavigate }: { onNavigate: () => void }) {
  return (
    <Link
      to={searchFocusPath}
      onClick={onNavigate}
      aria-label="Connect GitHub: search your username first"
      className={enabledClassName}
    >
      <GithubMark />
      Connect
    </Link>
  );
}

/** Pre: login is not empty. */
function ProfileConnectLink({ login, onNavigate }: ConnectGithubProps) {
  const [searchParams] = useSearchParams();
  const profileTokens = useProfileTokens(login, readConnectedKey(searchParams));
  if (profileTokens.isPending) {
    return (
      <button
        type="button"
        disabled
        aria-label="Connect GitHub"
        className={`${buttonClassName} cursor-not-allowed bg-night/40 text-white dark:bg-white/40 dark:text-night`}
      >
        <GithubMark />
        Connect
      </button>
    );
  }
  if (profileTokens.isError) {
    return <SearchFirstLink onNavigate={onNavigate} />;
  }
  const connectLabel = `Connect GitHub as ${profileTokens.data.login}`;
  return (
    <a
      href={profileTokens.data.installUrl}
      aria-label={connectLabel}
      title={connectLabel}
      className={enabledClassName}
    >
      <GithubMark />
      Connect
    </a>
  );
}

export function ConnectGithub({ login, onNavigate }: ConnectGithubProps) {
  return login === "" ? (
    <SearchFirstLink onNavigate={onNavigate} />
  ) : (
    <ProfileConnectLink login={login} onNavigate={onNavigate} />
  );
}
