import type { GithubLogin } from "./login";
import { activityCardPath, badgeCardPath, profileCardPath } from "./paths";
import type { Theme } from "./theme";

export type Badge = {
  readonly name: string;
  readonly description: string;
  readonly path: (login: GithubLogin, theme: Theme) => string;
};

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
  {
    name: "Activity",
    description: "A year of agent commits by day, shaded by tokens.",
    path: activityCardPath,
  },
];
