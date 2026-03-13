"use client";

import type { EdgeDetail } from "@/types/schemas";

interface Props {
  edges: EdgeDetail[];
}

export function EdgeTable({ edges }: Props) {
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
            <tr key={e.side} className="border-b border-gray-800/40">
              <td className="py-2 pr-4 font-medium text-white">{e.team}</td>
              <td className="text-right py-2 px-2 font-mono text-gray-300">
                {(e.calibrated_prob * 100).toFixed(1)}%
              </td>
              <td className="text-right py-2 px-2 font-mono text-gray-400">
                {(e.market_implied * 100).toFixed(1)}%
              </td>
              <td
                className={`text-right py-2 px-2 font-mono font-bold ${
                  e.edge_pct > 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                {e.edge_pct > 0 ? "+" : ""}
                {e.edge_pct.toFixed(1)}%
              </td>
              <td
                className={`text-right py-2 px-2 font-mono ${
                  e.ev_pct > 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                {e.ev_pct > 0 ? "+" : ""}
                {e.ev_pct.toFixed(1)}%
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

function TierBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    A: "bg-green-500/20 text-green-400",
    B: "bg-yellow-500/20 text-yellow-400",
    C: "bg-orange-500/20 text-orange-400",
    Pass: "bg-gray-600/20 text-gray-500",
  };
  return (
    <span
      className={`text-xs font-bold px-2 py-0.5 rounded-full ${colors[tier] ?? colors.Pass}`}
    >
      {tier}
    </span>
  );
}

function fmtOdds(n: number): string {
  return n >= 0 ? `+${n}` : `${n}`;
}
