import type { Theme } from "./theme";

/** Post: "/" when login is empty. */
export function profilePath(login: string): string {
  return `/${encodeURIComponent(login)}`;
}

export const searchFocusHash = "#search";
export const searchFocusPath = `/${searchFocusHash}`;

export function badgesPagePath(login: string): string {
  return login === "" ? "/badges" : `${profilePath(login)}/badges`;
}

export function avatarUrl(login: string): string {
  return `https://avatars.githubusercontent.com/${encodeURIComponent(login)}?size=64`;
}

export function profileCardPath(login: string, theme: Theme): string {
  return `/v1/badges/${encodeURIComponent(login)}/profile.svg?theme=${theme}`;
}

export function badgeCardPath(login: string, theme: Theme): string {
  return `/v1/badges/${encodeURIComponent(login)}.svg?theme=${theme}`;
}
