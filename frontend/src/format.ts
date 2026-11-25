export const compactNumberOptions: Intl.NumberFormatOptions = {
  notation: "compact",
  maximumFractionDigits: 1,
};

const compactNumber = new Intl.NumberFormat("en", compactNumberOptions);

export function formatTokens(tokens: number): string {
  return compactNumber.format(tokens);
}
