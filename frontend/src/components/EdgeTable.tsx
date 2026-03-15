"use client";

import type { EdgeDetail } from "@/types/schemas";
import { TierBadge } from "@/components/TierBadge";
import { fmtOdds, fmtPct, fmtProb } from "@/lib/format";

interface Props {
  edges: EdgeDetail[];
  onRowClick?: (edge: EdgeDetail) => void;
}

export function EdgeTable({ edges, onRowClick }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 text-xs uppercase tracking-wider border-b border-gray-700/50">
            <th className="text-left py-2 pr-4">Side</th>
            <th className="text-right py-2 px-2">Model</th>
            <th className="text-right py-2 px-2">Market</th>
            <th className="text-right py-2 px-2">Edge</th>
            <th className="text-right py-2 px-2">EV%</th>
            <th className="text-right py-2 px-2">Odds</th>
            <th className="text-center py-2 pl-2">Tier</th>
          </tr>
        </thead>
        <tbody>
          {edges.map((e) => (
            <tr
              key={e.side}
              className={`border-b border-gray-800/40 ${onRowClick ? "cursor-pointer hover:bg-gray-800/40 transition-colors" : ""}`}
              onClick={() => onRowClick?.(e)}
            >
              <td className="py-2 pr-4 font-medium text-white">{e.team}</td>
              <td className="text-right py-2 px-2 font-mono text-gray-300">
                {fmtProb(e.calibrated_prob)}
              </td>
              <td className="text-right py-2 px-2 font-mono text-gray-400">
                {fmtProb(e.market_implied)}
              </td>
              <td
                className={`text-right py-2 px-2 font-mono font-bold ${
                  e.edge_pct > 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                {fmtPct(e.edge_pct)}
              </td>
              <td
                className={`text-right py-2 px-2 font-mono ${
                  e.ev_pct > 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                {fmtPct(e.ev_pct)}
              </td>
              <td className="text-right py-2 px-2 font-mono text-gray-300">
                {fmtOdds(e.market_odds)}
              </td>
              <td className="text-center py-2 pl-2">
                <TierBadge tier={e.confidence_tier} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
