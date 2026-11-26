import type { GithubLogin } from "./login";
import {
  activityCardPath,
  badgeCardPath,
  profileCardPath,
  wideProfileCardPath,
} from "./paths";
import type { Theme } from "./theme";
import {
  activityWidget,
  cardWidget,
  profileWidget,
  type Widget,
  wideProfileWidget,
} from "./widget";

export type Badge = {
  readonly name: string;
  readonly description: string;
  readonly path: (login: GithubLogin, theme: Theme) => string;
  readonly widget: Widget;
};

export const badges: readonly Badge[] = [
  {
    name: "Profile",
    description: "Your photo, rarity, total tokens and top agents.",
    path: profileCardPath,
    widget: profileWidget,
  },
  {
    name: "Wide profile",
    description: "Your photo beside your rarity, total tokens and top agents.",
    path: wideProfileCardPath,
    widget: wideProfileWidget,
  },
  {
    name: "Card",
    description: "Rarity, total tokens and top agents, without the photo.",
    path: badgeCardPath,
    widget: cardWidget,
  },
  {
    name: "Activity",
    description: "A year of agent commits by day, shaded by tokens.",
    path: activityCardPath,
    widget: activityWidget,
  },
];
