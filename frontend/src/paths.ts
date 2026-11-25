import { z } from "zod";
import type { GithubLogin } from "./login";
import type { Theme } from "./theme";

export const homePath = "/";
export const badgesIndexPath = "/badges";
export const leaderboardPath = "/leaderboard";
export const searchFocusHash = "#search";
export const searchFocusPath = `${homePath}${searchFocusHash}`;

export function profilePath(login: GithubLogin): string {
  return `/${login}`;
}

export function badgesPagePath(login: GithubLogin): string {
  return `${profilePath(login)}/badges`;
}

export function userPath(login: GithubLogin): string {
  return `/v1/users/${login}`;
}

export function avatarUrl(login: GithubLogin): string {
  return `https://avatars.githubusercontent.com/${login}?size=64`;
}

export function profileCardPath(login: GithubLogin, theme: Theme): string {
  return `/v1/badges/${login}/profile.svg?theme=${theme}`;
}

export function badgeCardPath(login: GithubLogin, theme: Theme): string {
  return `/v1/badges/${login}.svg?theme=${theme}`;
}

export function activityCardPath(login: GithubLogin, theme: Theme): string {
  return `/v1/badges/${login}/activity.svg?theme=${theme}`;
}

// The uuid4().hex[:8] key the GitHub App setup redirect in backend/src/gittoken/api.py adds, so the CDN's
// copy from before the install is skipped.
const connectedKey = z
  .string()
  .regex(/^[0-9a-f]{8}$/)
  .brand<"ConnectedKey">();

export type ConnectedKey = z.infer<typeof connectedKey>;

/** Post: null when the URL has no connected key or it is malformed. */
export function parseConnectedKey(
  searchParams: URLSearchParams,
): ConnectedKey | null {
  const parsed = connectedKey.safeParse(searchParams.get("connected"));
  return parsed.success ? parsed.data : null;
}

export function withConnectedKey(
  path: string,
  key: ConnectedKey | null,
): string {
  const separator = path.includes("?") ? "&" : "?";
  return key === null ? path : `${path}${separator}connected=${key}`;
}
