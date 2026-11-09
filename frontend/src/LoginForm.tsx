import { type FormEvent, useState } from "react";
import { sendProfileSearchBeacon } from "./api";
import { glassClassName, pressableClassName } from "./glass";

type LoginFormProps = {
  initialLogin: string;
  submitLabel: string;
  onSubmitLogin: (login: string) => void;
};

export function LoginForm({
  initialLogin,
  submitLabel,
  onSubmitLogin,
}: LoginFormProps) {
  const [typedLogin, setTypedLogin] = useState(initialLogin);

  function submitLogin(event: FormEvent) {
    event.preventDefault();
    const login = typedLogin.trim();
    if (login !== "") {
      sendProfileSearchBeacon(login);
    }
    onSubmitLogin(login);
  }

  return (
    <form
      onSubmit={submitLogin}
      className={`flex w-full items-center gap-2 rounded-full p-1.5 pl-5 focus-within:ring-2 focus-within:ring-night/40 dark:focus-within:ring-white/40 ${glassClassName}`}
    >
      <label className="flex min-w-0 flex-1 flex-col">
        <span className="sr-only">GitHub username</span>
        <input
          value={typedLogin}
          onChange={(event) => setTypedLogin(event.target.value)}
          placeholder="GitHub user"
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
  );
}
