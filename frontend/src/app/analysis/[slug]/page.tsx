"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import type { GameAnalysisResponse, EdgeDetail } from "@/types/schemas";
import { TierBadge } from "@/components/TierBadge";
import { DataQualityBadge } from "@/components/DataQualityIndicator";
import { ProbabilityBar } from "@/components/ProbabilityBar";
import { RecommendationSummary } from "@/components/RecommendationSummary";
import { AnalysisTabs } from "@/components/AnalysisTabs";
import { analyzeGame } from "@/lib/api";

function bestTier(edges: EdgeDetail[]): string {
  if (edges.length === 0) return "Pass";
  if (edges.some((e) => e.confidence_tier === "A")) return "A";
  if (edges.some((e) => e.confidence_tier === "B")) return "B";
  if (edges.some((e) => e.confidence_tier === "C")) return "C";
  return "Pass";
}

function topEdge(edges: EdgeDetail[]): EdgeDetail | null {
  if (edges.length === 0) return null;
  return edges.reduce((best, e) => (e.edge_pct > best.edge_pct ? e : best), edges[0]);
}

function getDataQuality(analysis: GameAnalysisResponse): number {
  const meta = analysis.metadata as unknown as Record<string, unknown>;
  if (meta && "data_quality_score" in meta) return meta.data_quality_score as number;
  if (analysis.status === "success" && analysis.edges.length > 0) return 0.6;
  if (analysis.status === "success") return 0.5;
  return 0.3;
}

function fmtSpread(n: number): string {
  return n > 0 ? `+${n.toFixed(1)}` : n.toFixed(1);
}

export default function AnalysisDetailPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params.slug as string;
  const matchup = decodeURIComponent(slug);

  const [analysis, setAnalysis] = useState<GameAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const cached = sessionStorage.getItem(`analysis:${slug}`);
    if (cached) {
      try {
        setAnalysis(JSON.parse(cached));
      } catch {
        // ignore
      }
    }
  }, [slug]);

  const handleReanalyze = async () => {
    if (!analysis) return;
    setLoading(true);
    setError(null);
    try {
      const parts = analysis.matchup.split(" @ ");
      const result = await analyzeGame({
        home_team: parts[1] ?? "Home",
        away_team: parts[0] ?? "Away",
        league: analysis.league,
      });
      setAnalysis(result);
      sessionStorage.setItem(`analysis:${slug}`, JSON.stringify(result));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Re-analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const handleAddToWatchlist = () => {
    if (!analysis) return;
    const key = "omega_watchlist";
    const existing = JSON.parse(localStorage.getItem(key) ?? "[]") as unknown[];
    existing.push({
      matchup: analysis.matchup,
      league: analysis.league,
      analysis,
      addedAt: new Date().toISOString(),
    });
    localStorage.setItem(key, JSON.stringify(existing));
  };

  if (!analysis) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-8">
        <Link
          href="/"
          className="text-gray-400 hover:text-white transition-colors text-sm flex items-center gap-1 mb-6"
        >
          <span>&larr;</span> Slate
        </Link>
        <div className="text-center text-gray-600 py-16">
          <p className="text-lg">No analysis data for &ldquo;{matchup}&rdquo;</p>
          <p className="text-sm mt-2">Navigate from the slate to view a game analysis.</p>
        </div>
      </div>
    );
  }

  const sim = analysis.simulation;
  const tier = bestTier(analysis.edges);
  const edge = topEdge(analysis.edges);
  const dq = getDataQuality(analysis);

  return (
    <div className="max-w-5xl mx-auto px-6 py-4 overflow-y-auto h-full">
      {/* Sticky header */}
      <div className="sticky top-0 z-10 bg-gray-950/95 backdrop-blur -mx-6 px-6 py-3 mb-4 border-b border-gray-800/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-gray-400 hover:text-white transition-colors text-sm"
            >
              &larr; Slate
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white">{analysis.matchup}</h1>
              <p className="text-xs text-gray-400">
                {analysis.league} &middot;{" "}
                {new Date(analysis.analyzed_at).toLocaleDateString()} &middot;{" "}
                {new Date(analysis.analyzed_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <TierBadge tier={tier} size="md" />
            <DataQualityBadge score={dq} />
          </div>
        </div>
      </div>

      {/* Recommendation summary */}
      <div className="mb-6">
        <RecommendationSummary
          bestBet={analysis.best_bet}
          bestEdge={edge}
          dataQuality={dq}
          tier={tier}
        />
      </div>

      {/* Probability bar */}
      {sim && (
        <div className="mb-6">
          <ProbabilityBar
            homeProb={sim.home_win_prob}
            awayProb={sim.away_win_prob}
            drawProb={sim.draw_prob}
            homeTeam={analysis.matchup.split(" @ ")[1] ?? "Home"}
            awayTeam={analysis.matchup.split(" @ ")[0] ?? "Away"}
          />
        </div>
      )}

      {/* Simulation stats */}
      {sim && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <SimStat label="Predicted Spread" value={fmtSpread(sim.predicted_spread)} />
          <SimStat label="Predicted Total" value={sim.predicted_total.toFixed(1)} />
          <SimStat label="Home Score" value={sim.predicted_home_score.toFixed(1)} />
          <SimStat label="Away Score" value={sim.predicted_away_score.toFixed(1)} />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-400 text-sm mb-4">
          {error}
        </div>
      )}

      {/* Tabbed detail sections */}
      <div className="mb-8">
        <AnalysisTabs analysis={analysis} dataQuality={dq} />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pb-8 border-t border-gray-800 pt-4">
        <button
          onClick={handleAddToWatchlist}
          className="px-4 py-2 text-sm border border-gray-600 text-gray-300 hover:border-green-600 hover:text-green-400 rounded-lg transition-colors"
        >
          Add to Watchlist
        </button>
        <button
          onClick={handleReanalyze}
          disabled={loading}
          className="px-4 py-2 text-sm border border-gray-600 text-gray-300 hover:border-green-600 hover:text-green-400 rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? "Analyzing..." : "Re-analyze"}
        </button>
        <button
          onClick={() => router.push("/")}
          className="px-4 py-2 text-sm bg-green-600 hover:bg-green-500 text-white font-medium rounded-lg transition-colors"
        >
          Ask about this
        </button>
      </div>
    </div>
  );
}

function SimStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800/60 rounded-xl p-3 text-center">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-lg font-mono font-bold text-white mt-1">{value}</p>
    </div>
  );
}
