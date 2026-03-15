"use client";

import { TierBadge } from "@/components/TierBadge";
import { fmtOdds, fmtPct } from "@/lib/format";

const TIER_BORDER_COLORS: Record<string, string> = {
  A: "border-l-green-400",
  B: "border-l-yellow-400",
  C: "border-l-orange-400",
  Pass: "border-l-gray-600",
};

interface Props {
  selection: string;
  edgePct: number;
  tier: string;
  odds: number;
  league: string;
  onClick: () => void;
}

export function EdgeSummaryCard({ selection, edgePct, tier, odds, league, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className={`flex-shrink-0 w-[200px] bg-gray-800/60 rounded-xl border-l-4 ${
        TIER_BORDER_COLORS[tier] ?? TIER_BORDER_COLORS.Pass
      } p-3 text-left hover:bg-gray-800 transition-colors cursor-pointer`}
    >
      <p className="text-sm font-semibold text-white truncate">{selection}</p>
      <div className="flex items-center gap-2 mt-1.5">
        <span className="text-lg font-mono font-bold text-green-400">
          {fmtPct(edgePct)}
        </span>
        <TierBadge tier={tier} />
      </div>
      <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
        <span className="font-mono">{fmtOdds(odds)}</span>
        <span>{league}</span>
      </div>
    </button>
  );
}
