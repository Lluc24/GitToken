export type Badge = {
  name: string;
  description: string;
  path: (login: string) => string;
};

export function profileCardPath(login: string): string {
  return `/v1/badges/${encodeURIComponent(login)}/profile.svg`;
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
    path: (login) => `/v1/badges/${encodeURIComponent(login)}.svg`,
  },
];
