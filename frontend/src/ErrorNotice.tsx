import { glassClassName } from "./glass";

export function ErrorNotice({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className={`rounded-3xl px-5 py-3 text-rose-700 dark:text-rose-200 ${glassClassName}`}
    >
      {message}
    </p>
  );
}
