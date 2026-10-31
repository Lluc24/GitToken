import type { Theme } from "./theme";

export type Badge = {
  name: string;
  description: string;
  path: (login: string, theme: Theme) => string;
};

/** Pre: connectedKey is empty, or the key the GitHub App setup redirect added so the CDN's
 * copy from before the install is skipped. */
export function withConnectedKey(path: string, connectedKey: string): string {
  const separator = path.includes("?") ? "&" : "?";
  return connectedKey === ""
    ? path
    : `${path}${separator}connected=${encodeURIComponent(connectedKey)}`;
}

export function profileCardPath(login: string, theme: Theme): string {
  return `/v1/badges/${encodeURIComponent(login)}/profile.svg?theme=${theme}`;
}

export const badges: Badge[] = [
  {
    name: "Profile",
    description: "Your photo, rarity, total tokens and top agents.",
    path: profileCardPath,
  },
  {
    name: "Card",
    description: "Rarity, total tokens and top agents, without the photo.",
    path: (login, theme) =>
      `/v1/badges/${encodeURIComponent(login)}.svg?theme=${theme}`,
  },
];
