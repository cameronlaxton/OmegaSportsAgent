/** Shared formatting utilities. */

export function fmtOdds(n: number): string {
  return n >= 0 ? `+${n}` : `${n}`;
}

export function fmtPct(n: number, decimals = 1): string {
  const s = n.toFixed(decimals);
  return n > 0 ? `+${s}%` : `${s}%`;
}

export function fmtProb(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}
