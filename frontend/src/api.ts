import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

const rarityByLevel = {
  1: "common",
  2: "rare",
  3: "epic",
  4: "legendary",
  5: "champion",
} as const;

export type Rarity = (typeof rarityByLevel)[keyof typeof rarityByLevel];

const rarityLevel = z.union([
  z.literal(1),
  z.literal(2),
  z.literal(3),
  z.literal(4),
  z.literal(5),
]);

const profileTokensResponse = z.object({
  login: z.string(),
  total_tokens: z.number(),
  tokens_by_agent: z.record(z.string(), z.number()),
});

export type ProfileTokens = {
  login: string;
  totalTokens: number;
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
  const body = profileTokensResponse.parse(await response.json());
  return {
    login: body.login,
    totalTokens: body.total_tokens,
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

async function fetchRarity(tokens: number): Promise<Rarity> {
  const response = await fetch(`/v1/rarity?tokens=${tokens}`);
  if (!response.ok) {
    throw new Error(`The GitToken API answered ${response.status}`);
  }
  return rarityByLevel[rarityLevel.parse(await response.json())];
}

/** Pre: tokens >= 0. */
export function useRarity(tokens: number) {
  return useQuery({
    queryKey: ["rarity", tokens],
    queryFn: () => fetchRarity(tokens),
    retry: false,
  });
}
