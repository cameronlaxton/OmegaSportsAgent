"use client";

import type { BetSlip, EdgeDetail } from "@/types/schemas";
import { TierBadge } from "@/components/TierBadge";
import { fmtOdds, fmtPct, fmtProb } from "@/lib/format";

/** Quality threshold for recommendation vs analysis-only framing. */
const QUALITY_THRESHOLD = 0.6;
const RECOMMENDATION_TIERS = new Set(["A", "B"]);

interface Props {
  bestBet: BetSlip | null;
  bestEdge: EdgeDetail | null;
  dataQuality: number;
  tier: string;
}

export function RecommendationSummary({ bestBet, bestEdge, dataQuality, tier }: Props) {
  const isRecommendation =
    RECOMMENDATION_TIERS.has(tier) && dataQuality >= QUALITY_THRESHOLD && bestBet !== null;

  const edge = bestBet ?? bestEdge;
  if (!edge) {
    return (
      <div className="bg-gray-800/60 border border-gray-700 rounded-2xl p-6">
        <p className="text-sm text-gray-400">No edge detected for this matchup.</p>
      </div>
    );
  }

  return (
    <div
      className={`rounded-2xl p-6 ${
        isRecommendation
          ? "bg-gradient-to-r from-green-900/40 to-green-800/20 border border-green-500/30"
          : "bg-gray-800/60 border border-gray-700"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span
          className={`text-xs font-bold uppercase tracking-wider ${
            isRecommendation ? "text-green-400" : "text-gray-500"
          }`}
        >
          {isRecommendation ? "Recommendation" : "Analysis"}
        </span>
        <TierBadge tier={tier} size="md" />
      </div>

      {/* Selection */}
      <p className="text-xl font-bold text-white mb-4">
        {bestBet?.selection ?? `${bestEdge?.team} (${bestEdge?.side})`}
      </p>

      {/* Primary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-3">
        <Stat label="Edge" value={fmtPct("edge_pct" in edge ? edge.edge_pct : 0)} positive />
        <Stat
          label="EV"
          value={fmtPct("ev_pct" in edge ? edge.ev_pct : 0)}
          positive={"ev_pct" in edge && edge.ev_pct > 0}
        />
        <Stat
          label="Odds"
          value={fmtOdds("odds" in edge ? (edge as BetSlip).odds : (edge as EdgeDetail).market_odds)}
        />
        {isRecommendation && bestBet ? (
          <Stat label="Units" value={`${bestBet.recommended_units.toFixed(1)}u`} />
        ) : (
          <Stat label="Data Quality" value={`${(dataQuality * 100).toFixed(0)}%`} />
        )}
      </div>

      {/* Secondary stats */}
      <div className="grid grid-cols-3 gap-4 text-xs">
        {bestBet && (
          <div>
            <span className="text-gray-500 uppercase">Kelly</span>
            <p className="text-gray-300 font-mono mt-0.5">
              {(bestBet.kelly_fraction * 100).toFixed(1)}%
            </p>
          </div>
        )}
        {bestEdge && (
          <>
            <div>
              <span className="text-gray-500 uppercase">Model Prob</span>
              <p className="text-gray-300 font-mono mt-0.5">
                {fmtProb(bestEdge.calibrated_prob)}
              </p>
            </div>
            <div>
              <span className="text-gray-500 uppercase">Market Implied</span>
              <p className="text-gray-300 font-mono mt-0.5">
                {fmtProb(bestEdge.market_implied)}
              </p>
            </div>
          </>
        )}
      </div>

      {/* Caveat for non-recommendation */}
      {!isRecommendation && (
        <p className="mt-4 text-xs text-yellow-400/80">
          {dataQuality < QUALITY_THRESHOLD
            ? "Data quality below threshold for directional recommendation."
            : tier === "Pass"
              ? "Edge below confidence threshold."
              : "Confidence tier insufficient for directional recommendation."}
        </p>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive?: boolean;
}) {
  return (
    <div className="text-center">
      <p className="text-xs text-gray-500 uppercase">{label}</p>
      <p
        className={`text-sm font-mono font-bold mt-1 ${
          positive ? "text-green-400" : "text-white"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
