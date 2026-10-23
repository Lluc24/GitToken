import type { Theme } from "./theme";

export type Badge = {
  name: string;
  description: string;
  path: (login: string, theme: Theme) => string;
};

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
