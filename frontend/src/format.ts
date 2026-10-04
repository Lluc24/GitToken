const compactNumber = new Intl.NumberFormat("en", {
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatTokens(tokens: number): string {
  return compactNumber.format(tokens);
}
