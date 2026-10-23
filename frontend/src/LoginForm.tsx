import { type FormEvent, useState } from "react";
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
    onSubmitLogin(typedLogin.trim());
  }

  return (
    <form
      onSubmit={submitLogin}
      className={`flex w-full items-center gap-2 rounded-full p-1.5 pl-6 focus-within:ring-2 focus-within:ring-ink/40 ${glassClassName}`}
    >
      <label className="flex flex-1 flex-col">
        <span className="sr-only">GitHub username</span>
        <input
          value={typedLogin}
          onChange={(event) => setTypedLogin(event.target.value)}
          placeholder="GitHub username"
          className="w-full bg-transparent py-2 text-lg text-ink outline-none placeholder:text-ink/40"
        />
      </label>
      <button
        type="submit"
        className={`rounded-full bg-gradient-to-br from-cyan-300 via-violet-400 to-fuchsia-400 px-6 py-3 font-semibold text-night shadow-[inset_0_1px_0_rgb(255_255_255/0.7),0_8px_30px_-6px_rgb(167_139_250/0.8)] ${pressableClassName}`}
      >
        {submitLabel}
      </button>
    </form>
  );
}
