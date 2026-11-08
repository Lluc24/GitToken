/** Post: "/" when login is empty. */
export function profilePath(login: string): string {
  return `/${encodeURIComponent(login)}`;
}

export function badgesPagePath(login: string): string {
  return login === "" ? "/badges" : `${profilePath(login)}/badges`;
}

export function avatarUrl(login: string): string {
  return `https://avatars.githubusercontent.com/${encodeURIComponent(login)}?size=64`;
}
