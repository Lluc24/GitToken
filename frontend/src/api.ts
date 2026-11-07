import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { withConnectedKey } from "./badges";

const rarity = z.enum(["common", "rare", "epic", "legendary", "champion"]);

export type Rarity = z.infer<typeof rarity>;

/** Post: the JSON body parsed by schema, or an Error naming source when it is unreadable or unexpected. */
async function parseBody<T>(
  response: Response,
  schema: z.ZodType<T>,
  source: string,
): Promise<T> {
  let rawBody: unknown;
  try {
    rawBody = await response.json();
  } catch {
    throw new Error(`${source} returned an unreadable response`);
  }
  const parsed = schema.safeParse(rawBody);
  if (!parsed.success) {
    throw new Error(`${source} returned an unexpected response`);
  }
  return parsed.data;
}

const profileTokensResponse = z.object({
  login: z.string(),
  total_tokens: z.number(),
  rarity,
  tokens_by_agent: z.record(z.string(), z.number()),
  includes_private_repositories: z.boolean(),
});

export type ProfileTokens = {
  login: string;
  totalTokens: number;
  rarity: Rarity;
  tokensByAgent: Record<string, number>;
  includesPrivateRepositories: boolean;
};

async function fetchProfileTokens(
  login: string,
  connectedKey: string,
): Promise<ProfileTokens> {
  const response = await fetch(
    withConnectedKey(`/v1/users/${encodeURIComponent(login)}`, connectedKey),
  );
  if (response.status === 404) {
    throw new Error(`No GitHub user named ${login}`);
  }
  if (response.status === 422) {
    throw new Error(`${login} is not a valid GitHub username`);
  }
  if (!response.ok) {
    throw new Error(`The GitToken API answered ${response.status}`);
  }
  const body = await parseBody(
    response,
    profileTokensResponse,
    "The GitToken API",
  );
  return {
    login: body.login,
    totalTokens: body.total_tokens,
    rarity: body.rarity,
    tokensByAgent: body.tokens_by_agent,
    includesPrivateRepositories: body.includes_private_repositories,
  };
}

/** Pre: login is not empty. */
export function useProfileTokens(login: string, connectedKey: string) {
  return useQuery({
    queryKey: ["profile-tokens", login, connectedKey],
    queryFn: () => fetchProfileTokens(login, connectedKey),
    retry: false,
  });
}

const leaderboardResponse = z.array(
  z.object({
    login: z.string(),
    total_tokens: z.number(),
    rarity,
  }),
);

export type LeaderboardEntry = {
  login: string;
  totalTokens: number;
  rarity: Rarity;
};

async function fetchLeaderboard(): Promise<LeaderboardEntry[]> {
  const response = await fetch("/v1/leaderboard");
  if (!response.ok)
    throw new Error("The leaderboard is unavailable right now.");
  const body = await parseBody(
    response,
    leaderboardResponse,
    "The leaderboard",
  );
  return body.map((entry) => ({
    login: entry.login,
    totalTokens: entry.total_tokens,
    rarity: entry.rarity,
  }));
}

export function useLeaderboard() {
  return useQuery({
    queryKey: ["leaderboard"],
    queryFn: fetchLeaderboard,
    retry: false,
  });
}

const githubAppResponse = z.object({
  install_url: z.url({ protocol: /^https$/, hostname: /^github\.com$/ }),
});

export type GithubApp =
  | { isConfigured: true; installUrl: string }
  | { isConfigured: false };

async function fetchGithubApp(): Promise<GithubApp> {
  const response = await fetch("/v1/github-app");
  if (response.status === 503) {
    return { isConfigured: false };
  }
  if (!response.ok) {
    throw new Error(`The GitToken API answered ${response.status}`);
  }
  const body = await parseBody(response, githubAppResponse, "The GitToken API");
  return { isConfigured: true, installUrl: body.install_url };
}

export function useGithubApp() {
  return useQuery({
    queryKey: ["github-app"],
    queryFn: fetchGithubApp,
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  });
}
