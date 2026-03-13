"use client";

import type { BetSlip } from "@/types/schemas";

interface Props {
  slip: BetSlip;
}

export function BetSlipCard({ slip }: Props) {
  return (
    <div className="bg-gradient-to-r from-green-900/40 to-green-800/20 border border-green-500/30 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-green-400 text-lg font-bold">Best Bet</span>
        <span
          className={`text-xs font-bold px-2 py-0.5 rounded-full ${
            slip.confidence_tier === "A"
              ? "bg-green-500/20 text-green-400"
              : "bg-yellow-500/20 text-yellow-400"
          }`}
        >
          Tier {slip.confidence_tier}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
        <div>
          <p className="text-xs text-gray-500 uppercase">Selection</p>
          <p className="text-sm font-bold text-white mt-1">{slip.selection}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase">Odds</p>
          <p className="text-sm font-mono font-bold text-white mt-1">
            {slip.odds >= 0 ? `+${slip.odds}` : slip.odds}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase">Edge</p>
          <p className="text-sm font-mono font-bold text-green-400 mt-1">
            +{slip.edge_pct.toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase">Units</p>
          <p className="text-sm font-mono font-bold text-white mt-1">
            {slip.recommended_units.toFixed(2)}u
          </p>
        </div>
      </div>
    </div>
  );
}
