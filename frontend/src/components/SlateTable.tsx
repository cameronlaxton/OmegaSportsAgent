"use client";

import type { GameAnalysisResponse } from "@/types/schemas";
import { TierBadge } from "@/components/TierBadge";
import { DataQualityDot } from "@/components/DataQualityIndicator";
import { fmtPct } from "@/lib/format";

interface Props {
  analyses: GameAnalysisResponse[];
  onRowClick: (analysis: GameAnalysisResponse) => void;
}

function bestEdge(analysis: GameAnalysisResponse): number {
  if (!analysis.edges || analysis.edges.length === 0) return 0;
  return Math.max(...analysis.edges.map((e) => e.edge_pct));
}

function bestTier(analysis: GameAnalysisResponse): string {
  if (!analysis.edges || analysis.edges.length === 0) return "Pass";
  const tiers = analysis.edges.map((e) => e.confidence_tier);
  if (tiers.includes("A")) return "A";
  if (tiers.includes("B")) return "B";
  if (tiers.includes("C")) return "C";
  return "Pass";
}

function dataQuality(analysis: GameAnalysisResponse): number {
  // Extract from metadata or structured data if available; default 0.5
  const meta = analysis.metadata as Record<string, unknown> | undefined;
  if (meta && typeof meta === "object" && "data_quality_score" in meta) {
    return meta.data_quality_score as number;
  }
  // Heuristic: if analysis succeeded with edges, assume decent quality
  if (analysis.status === "success" && analysis.edges.length > 0) return 0.6;
  if (analysis.status === "success") return 0.5;
  return 0.3;
}

function statusIcon(status: string): string {
  switch (status) {
    case "success":
      return "\u2713";
    case "skipped":
      return "\u26a0";
    case "error":
      return "\u2717";
    default:
      return "?";
  }
}

function statusColor(status: string): string {
  switch (status) {
    case "success":
      return "text-green-400";
    case "skipped":
      return "text-yellow-400";
    case "error":
      return "text-red-400";
    default:
      return "text-gray-500";
  }
}

export function SlateTable({ analyses, onRowClick }: Props) {
  if (analyses.length === 0) {
    return (
      <div className="text-center text-gray-600 py-16 space-y-3">
        <p className="text-lg">No games analyzed yet</p>
        <p className="text-sm">Use the &ldquo;Analyze Slate&rdquo; button to get started.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 text-xs uppercase tracking-wider border-b border-gray-700/50">
            <th className="text-left py-2 pr-2 w-16">Time</th>
            <th className="text-left py-2 px-2">Matchup</th>
            <th className="text-right py-2 px-2 w-20">Spread</th>
            <th className="text-right py-2 px-2 w-20">Total</th>
            <th className="text-right py-2 px-2 w-20">Edge</th>
            <th className="text-center py-2 px-2 w-16">Tier</th>
            <th className="text-center py-2 px-2 w-12">DQ</th>
            <th className="text-center py-2 pl-2 w-8"></th>
          </tr>
        </thead>
        <tbody>
          {analyses.map((a, i) => {
            const edge = bestEdge(a);
            const tier = bestTier(a);
            const dq = dataQuality(a);
            const time = a.analyzed_at
              ? new Date(a.analyzed_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
              : "--";

            return (
              <tr
                key={`${a.matchup}-${i}`}
                className="border-b border-gray-800/40 cursor-pointer hover:bg-gray-800/40 transition-colors"
                onClick={() => onRowClick(a)}
              >
                <td className="py-2.5 pr-2 text-xs text-gray-500">{time}</td>
                <td className="py-2.5 px-2 font-medium text-white">{a.matchup}</td>
                <td className="text-right py-2.5 px-2 font-mono text-gray-300">
                  {a.simulation ? a.simulation.predicted_spread.toFixed(1) : "--"}
                </td>
                <td className="text-right py-2.5 px-2 font-mono text-gray-300">
                  {a.simulation ? a.simulation.predicted_total.toFixed(1) : "--"}
                </td>
                <td
                  className={`text-right py-2.5 px-2 font-mono font-bold ${
                    edge > 0 ? "text-green-400" : "text-gray-500"
                  }`}
                >
                  {edge !== 0 ? fmtPct(edge) : "--"}
                </td>
                <td className="text-center py-2.5 px-2">
                  <TierBadge tier={tier} />
                </td>
                <td className="text-center py-2.5 px-2">
                  <DataQualityDot score={dq} />
                </td>
                <td className={`text-center py-2.5 pl-2 text-xs ${statusColor(a.status)}`}>
                  {statusIcon(a.status)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Skeleton loading state for the slate table. */
export function SlateTableSkeleton() {
  return (
    <div className="space-y-0">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 py-3 border-b border-gray-800/40 animate-pulse"
        >
          <div className="w-12 h-3 bg-gray-800 rounded" />
          <div className="flex-1 h-3 bg-gray-800 rounded" />
          <div className="w-14 h-3 bg-gray-800 rounded" />
          <div className="w-14 h-3 bg-gray-800 rounded" />
          <div className="w-14 h-3 bg-gray-800 rounded" />
          <div className="w-10 h-5 bg-gray-800 rounded-full" />
          <div className="w-2 h-2 bg-gray-800 rounded-full" />
        </div>
      ))}
    </div>
  );
}
