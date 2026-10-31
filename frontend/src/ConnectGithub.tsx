import type { UseQueryResult } from "@tanstack/react-query";
import { useId, useState } from "react";
import { type GithubApp, useGithubApp } from "./api";
import { glassClassName, pressableClassName } from "./glass";

const connectLabel = "Connect GitHub to also scan your private repos";

function GithubMark() {
  return (
    <svg
      viewBox="0 0 16 16"
      className="size-5 shrink-0"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z" />
    </svg>
  );
}

function statusMessage(githubApp: UseQueryResult<GithubApp>): string {
  if (githubApp.isError) {
    return "Couldn't check whether private repo scanning is available";
  }
  if (githubApp.isPending) {
    return "";
  }
  if (githubApp.data.isConfigured) {
    return "Your total and per-agent breakdown become public. Repo names, commits and code are never stored or shown.";
  }
  return "Private repo scanning isn't available yet";
}

export function ConnectGithub() {
  const githubApp = useGithubApp();
  const statusId = useId();
  const buttonClassName = `flex items-center gap-2 rounded-full px-5 py-2.5 font-medium text-sm ${glassClassName}`;
  return (
    <div className="flex max-w-sm flex-col items-center gap-2 text-center">
      {githubApp.data?.isConfigured ? (
        <a
          href={githubApp.data.installUrl}
          aria-describedby={statusId}
          className={`${buttonClassName} text-night dark:text-white ${pressableClassName}`}
        >
          <GithubMark />
          {connectLabel}
        </a>
      ) : (
        <button
          type="button"
          disabled
          aria-describedby={statusId}
          className={`${buttonClassName} cursor-not-allowed text-night/40 dark:text-white/40`}
        >
          <GithubMark />
          {connectLabel}
        </button>
      )}
      <p
        id={statusId}
        role={githubApp.isError ? "alert" : "status"}
        className="text-night/60 text-xs dark:text-white/60"
      >
        {statusMessage(githubApp)}
      </p>
    </div>
  );
}

export function ConnectGithubMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const panelId = useId();
  return (
    <div>
      <button
        type="button"
        aria-label="GitHub"
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={() => setIsOpen(!isOpen)}
        className="flex size-10 items-center justify-center rounded-full text-night/80 hover:bg-night/15 hover:text-night sm:size-9 dark:text-white/80 dark:hover:bg-white/15 dark:hover:text-white"
      >
        <GithubMark />
      </button>
      {isOpen && (
        <div
          id={panelId}
          className="absolute top-full right-0 mt-3 w-80 max-w-full rounded-3xl border border-white/90 bg-white/95 p-4 shadow-[0_24px_60px_-28px_rgb(15_23_42/0.4)] backdrop-blur-xl dark:border-white/20 dark:bg-night/95"
        >
          <ConnectGithub />
          <a
            href="https://github.com/Lluc24/GitToken"
            className="mt-3 block border-night/10 border-t pt-3 text-center text-night/70 text-sm hover:text-night dark:border-white/10 dark:text-white/70 dark:hover:text-white"
          >
            GitToken's source on GitHub
          </a>
        </div>
      )}
    </div>
  );
}
