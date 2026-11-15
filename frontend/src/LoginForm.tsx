import { type FormEvent, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { sendProfileSearchBeacon } from "./api";
import { glassClassName, pressableClassName } from "./glass";
import { type GithubLogin, parseGithubLogin } from "./login";
import { searchFocusHash } from "./paths";

type LoginFormProps = {
  initialLogin: string;
  submitLabel: string;
  onSubmitLogin: (login: GithubLogin) => void;
};

export function LoginForm({
  initialLogin,
  submitLabel,
  onSubmitLogin,
}: LoginFormProps) {
  const [typedLogin, setTypedLogin] = useState(initialLogin);
  const [isInvalid, setIsInvalid] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const location = useLocation();
  const isSearchFocusRequested = location.hash === searchFocusHash;

  useEffect(() => {
    if (location.hash === searchFocusHash) {
      inputRef.current?.focus();
    }
  }, [location]);

  function submitLogin(event: FormEvent) {
    event.preventDefault();
    const login = parseGithubLogin(typedLogin.trim());
    setIsInvalid(login === null);
    if (login !== null) {
      onSubmitLogin(login);
      sendProfileSearchBeacon(login);
    }
  }

  return (
    <div className="flex w-full flex-col gap-2">
      <form
        onSubmit={submitLogin}
        className={`flex w-full items-center gap-2 rounded-full p-1.5 pl-5 focus-within:ring-2 focus-within:ring-night/40 dark:focus-within:ring-white/40 ${glassClassName}`}
      >
        <label className="flex min-w-0 flex-1 flex-col">
          <span className="sr-only">GitHub username</span>
          <input
            ref={inputRef}
            value={typedLogin}
            onChange={(event) => {
              setTypedLogin(event.target.value);
              setIsInvalid(false);
            }}
            aria-invalid={isInvalid}
            aria-describedby={isInvalid ? "login-error" : undefined}
            placeholder={
              isSearchFocusRequested ? "Your GitHub username" : "GitHub user"
            }
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            enterKeyHint="search"
            className="w-full bg-transparent py-2 text-base text-night sm:text-lg dark:text-white outline-none placeholder:text-night/40 dark:placeholder:text-white/40"
          />
        </label>
        <button
          type="submit"
          className={`shrink-0 whitespace-nowrap rounded-full bg-gradient-to-br from-cyan-300 via-violet-400 to-fuchsia-400 px-5 py-3 font-semibold sm:px-6 text-night shadow-[inset_0_1px_0_rgb(255_255_255/0.7),0_8px_30px_-6px_rgb(167_139_250/0.8)] ${pressableClassName}`}
        >
          {submitLabel}
        </button>
      </form>
      {isInvalid && (
        <p
          id="login-error"
          role="alert"
          className="px-5 text-rose-700 text-sm dark:text-rose-200"
        >
          Enter a GitHub username: letters, numbers and hyphens, up to 39
          characters.
        </p>
      )}
    </div>
  );
}
