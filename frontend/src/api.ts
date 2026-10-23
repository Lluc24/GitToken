import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

const rarity = z.enum(["common", "rare", "epic", "legendary", "champion"]);

export type Rarity = z.infer<typeof rarity>;

const profileTokensResponse = z.object({
  login: z.string(),
  total_tokens: z.number(),
  rarity,
  tokens_by_agent: z.record(z.string(), z.number()),
});

export type ProfileTokens = {
  login: string;
  totalTokens: number;
  rarity: Rarity;
  tokensByAgent: Record<string, number>;
};

async function fetchProfileTokens(login: string): Promise<ProfileTokens> {
  const response = await fetch(`/v1/users/${encodeURIComponent(login)}`);
  if (response.status === 404) {
    throw new Error(`No GitHub user named ${login}`);
  }
  if (response.status === 422) {
    throw new Error(`${login} is not a valid GitHub username`);
  }
  if (!response.ok) {
    throw new Error(`The GitToken API answered ${response.status}`);
  }
  let rawBody: unknown;
  try {
    rawBody = await response.json();
  } catch {
    throw new Error("The GitToken API returned an unreadable response");
  }
  const parsed = profileTokensResponse.safeParse(rawBody);
  if (!parsed.success) {
    throw new Error("The GitToken API returned an unexpected response");
  }
  const body = parsed.data;
  return {
    login: body.login,
    totalTokens: body.total_tokens,
    rarity: body.rarity,
    tokensByAgent: body.tokens_by_agent,
  };
}

/** Pre: login is not empty. */
export function useProfileTokens(login: string) {
  return useQuery({
    queryKey: ["profile-tokens", login],
    queryFn: () => fetchProfileTokens(login),
    retry: false,
  });
}

const leaderboardResponse = z.array(
  z.object({ login: z.string(), total_tokens: z.number() }),
);

async function fetchLeaderboard() {
  const response = await fetch("/v1/leaderboard");
  if (!response.ok)
    throw new Error("The leaderboard is unavailable right now.");
  return leaderboardResponse.parse(await response.json());
}

export function useLeaderboard() {
  return useQuery({
    queryKey: ["leaderboard"],
    queryFn: fetchLeaderboard,
    retry: false,
  });
}
