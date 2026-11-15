import { z } from "zod";

// The same rule as GITHUB_LOGIN_PATTERN in backend/src/gittoken/domain.py.
export const githubLogin = z
  .string()
  .regex(/^[A-Za-z0-9][A-Za-z0-9-]{0,38}$/)
  .brand<"GithubLogin">();

export type GithubLogin = z.infer<typeof githubLogin>;

/** Post: null when raw is not a GitHub login. */
export function parseGithubLogin(raw: string): GithubLogin | null {
  const parsed = githubLogin.safeParse(raw);
  return parsed.success ? parsed.data : null;
}

/** Post: null when the route has no :login or it is not a GitHub login. */
export function parseRouteLogin(
  routeLogin: string | undefined,
): GithubLogin | null {
  return routeLogin === undefined ? null : parseGithubLogin(routeLogin);
}

export function invalidLoginMessage(routeLogin: string): string {
  return `${routeLogin} is not a valid GitHub username`;
}
