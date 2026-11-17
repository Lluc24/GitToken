import { SegmentedControl } from "./SegmentedControl";
import { setTheme, type Theme, themes, useTheme } from "./theme";

const iconPathsByTheme: Record<Theme, string[]> = {
  light: [
    "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z",
    "M12 1v2m0 18v2M4.2 4.2l1.4 1.4m12.8 12.8 1.4 1.4M1 12h2m18 0h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  ],
  dark: ["M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"],
};

function ThemeIcon({ theme }: { theme: Theme }) {
  return (
    <>
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
      <span className="sr-only">{theme} theme</span>
    </>
  );
}

export function ThemeToggle() {
  const selectedTheme = useTheme();
  return (
    <SegmentedControl
      label="Theme"
      variant="icon"
      options={themes}
      selected={selectedTheme}
      onSelect={setTheme}
      renderOption={(theme) => <ThemeIcon theme={theme} />}
    />
  );
}
