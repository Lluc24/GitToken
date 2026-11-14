import { badgeCardPath, profileCardPath } from "./paths";
import type { Theme } from "./theme";

export type Badge = {
  readonly name: string;
  readonly description: string;
  readonly path: (login: string, theme: Theme) => string;
};

/** Pre: connectedKey is empty, or the key the GitHub App setup redirect added so the CDN's
 * copy from before the install is skipped. */
export function withConnectedKey(path: string, connectedKey: string): string {
  const separator = path.includes("?") ? "&" : "?";
  return connectedKey === ""
    ? path
    : `${path}${separator}connected=${encodeURIComponent(connectedKey)}`;
}

export function readConnectedKey(searchParams: URLSearchParams): string {
  return searchParams.get("connected") ?? "";
}

export const badges: readonly Badge[] = [
  {
    name: "Profile",
    description: "Your photo, rarity, total tokens and top agents.",
    path: profileCardPath,
  },
  {
    name: "Card",
    description: "Rarity, total tokens and top agents, without the photo.",
    path: badgeCardPath,
  },
];
