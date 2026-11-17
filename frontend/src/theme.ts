import { useSyncExternalStore } from "react";

export const themes = ["light", "dark"] as const;

export type Theme = (typeof themes)[number];

const listeners = new Set<() => void>();

// index.html sets data-theme before the first paint, from localStorage or the system setting.
function currentTheme(): Theme {
  return document.documentElement.getAttribute("data-theme") === "light"
    ? "light"
    : "dark";
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function setTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("theme", theme);
  for (const listener of listeners) {
    listener();
  }
}

export function useTheme(): Theme {
  return useSyncExternalStore(subscribe, currentTheme);
}
