import { setTheme, type Theme, useTheme } from "./theme";

const iconPathsByTheme: Record<Theme, string[]> = {
  light: [
    "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z",
    "M12 1v2m0 18v2M4.2 4.2l1.4 1.4m12.8 12.8 1.4 1.4M1 12h2m18 0h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  ],
  dark: ["M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"],
};

export function ThemeToggle() {
  const selectedTheme = useTheme();
  return (
    <fieldset className="flex rounded-full bg-ink/10 p-0.5">
      <legend className="sr-only">Theme</legend>
      {(["light", "dark"] as const).map((theme) => (
        <button
          key={theme}
          type="button"
          aria-label={`${theme} theme`}
          aria-pressed={theme === selectedTheme}
          onClick={() => setTheme(theme)}
          className={`flex size-8 items-center justify-center rounded-full transition-colors ${theme === selectedTheme ? "bg-ink text-canvas" : "text-ink/60 hover:text-ink"}`}
        >
          <svg
            viewBox="0 0 24 24"
            className="size-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            {iconPathsByTheme[theme].map((path) => (
              <path key={path} d={path} />
            ))}
          </svg>
        </button>
      ))}
    </fieldset>
  );
}
