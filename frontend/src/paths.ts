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
