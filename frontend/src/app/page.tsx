"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { analyzeSlate } from "@/lib/api";
import type { GameAnalysisResponse, SlateAnalysisResponse } from "@/types/schemas";
import {
  FilterSidebar,
  type League,
  type DateOption,
  type EdgeFilter,
  type SortOption,
} from "@/components/FilterSidebar";
import { SlateTable, SlateTableSkeleton } from "@/components/SlateTable";
import { EdgeSummaryCard } from "@/components/EdgeSummaryCard";
import { ChatPanel } from "@/components/ChatPanel";

function dateForOption(option: DateOption): string {
  const d = new Date();
  if (option === "Yesterday") d.setDate(d.getDate() - 1);
  if (option === "Tomorrow") d.setDate(d.getDate() + 1);
  return d.toISOString().split("T")[0];
}

function bestEdgeFromAnalysis(a: GameAnalysisResponse): number {
  if (!a.edges || a.edges.length === 0) return 0;
  return Math.max(...a.edges.map((e) => e.edge_pct));
}

function bestTierFromAnalysis(a: GameAnalysisResponse): string {
  if (!a.edges || a.edges.length === 0) return "Pass";
  const tiers = a.edges.map((e) => e.confidence_tier);
  if (tiers.includes("A")) return "A";
  if (tiers.includes("B")) return "B";
  if (tiers.includes("C")) return "C";
  return "Pass";
}

export default function Home() {
  const router = useRouter();

  // Filter state
  const [league, setLeague] = useState<League>("NBA");
  const [dateOption, setDateOption] = useState<DateOption>("Today");
  const [customDate, setCustomDate] = useState<string | null>(null);
  const [edgeFilter, setEdgeFilter] = useState<EdgeFilter>("All Games");
  const [sortBy, setSortBy] = useState<SortOption>("By Time");

  // Slate data
  const [slateResponse, setSlateResponse] = useState<SlateAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selected game context for chat
  const [chatContext, setChatContext] = useState<string | null>(null);

  const effectiveDate = customDate ?? dateForOption(dateOption);

  const handleAnalyzeSlate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeSlate({ league, date: effectiveDate });
      setSlateResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze slate");
    } finally {
      setLoading(false);
    }
  }, [league, effectiveDate]);

  const handleRowClick = useCallback(
    (analysis: GameAnalysisResponse) => {
      const slug = encodeURIComponent(analysis.matchup);
      // Store analysis in sessionStorage for the detail page
      sessionStorage.setItem(`analysis:${slug}`, JSON.stringify(analysis));
      router.push(`/analysis/${slug}`);
    },
    [router],
  );

  // Filter and sort analyses
  const filteredAnalyses = (() => {
    if (!slateResponse) return [];
    let list = [...slateResponse.analyses];

    // Edge filter
    if (edgeFilter === "Edges Only") {
      list = list.filter((a) => bestEdgeFromAnalysis(a) > 0);
    } else if (edgeFilter === "Tier A/B") {
      list = list.filter((a) => {
        const tier = bestTierFromAnalysis(a);
        return tier === "A" || tier === "B";
      });
    }

    // Sort
    if (sortBy === "By Edge") {
      list.sort((a, b) => bestEdgeFromAnalysis(b) - bestEdgeFromAnalysis(a));
    } else if (sortBy === "By Confidence") {
      const tierRank: Record<string, number> = { A: 0, B: 1, C: 2, Pass: 3 };
      list.sort(
        (a, b) =>
          (tierRank[bestTierFromAnalysis(a)] ?? 3) - (tierRank[bestTierFromAnalysis(b)] ?? 3),
      );
    }
    // "By Time" is default order from API

    return list;
  })();

  // Top edges for the summary strip (max 5, must have edge > 0)
  const topEdges = (() => {
    if (!slateResponse) return [];
    return slateResponse.analyses
      .filter((a) => a.status === "success" && a.best_bet)
      .sort((a, b) => bestEdgeFromAnalysis(b) - bestEdgeFromAnalysis(a))
      .slice(0, 5);
  })();

  // Stats for sidebar
  const stats = slateResponse
    ? {
        totalGames: slateResponse.total_games,
        gamesWithEdge: slateResponse.games_with_edge,
        tierACount: slateResponse.analyses.filter((a) => bestTierFromAnalysis(a) === "A").length,
      }
    : null;

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left sidebar */}
      <FilterSidebar
        league={league}
        dateOption={dateOption}
        customDate={customDate}
        edgeFilter={edgeFilter}
        sortBy={sortBy}
        stats={stats}
        onLeagueChange={(l) => {
          setLeague(l);
          setSlateResponse(null);
        }}
        onDateChange={(d) => {
          setDateOption(d);
          setCustomDate(null);
          setSlateResponse(null);
        }}
        onCustomDateChange={(d) => {
          setCustomDate(d);
          setSlateResponse(null);
        }}
        onEdgeFilterChange={setEdgeFilter}
        onSortChange={setSortBy}
      />

      {/* Main content */}
      <main className="flex-1 overflow-y-auto px-6 py-4">
        {/* Edge summary strip */}
        {topEdges.length > 0 && (
          <div className="mb-4">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Top Edges
            </h2>
            <div className="flex gap-3 overflow-x-auto pb-2">
              {topEdges.map((a, i) => {
                const bet = a.best_bet!;
                return (
                  <EdgeSummaryCard
                    key={`${a.matchup}-${i}`}
                    selection={bet.selection}
                    edgePct={bet.edge_pct}
                    tier={bet.confidence_tier}
                    odds={bet.odds}
                    league={a.league}
                    onClick={() => {
                      setChatContext(a.matchup);
                      handleRowClick(a);
                    }}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* Slate controls + table */}
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-400">
            {league} &middot; {effectiveDate}
          </h2>
          <button
            onClick={handleAnalyzeSlate}
            disabled={loading}
            className="px-4 py-1.5 text-sm bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors"
          >
            {loading ? "Analyzing..." : slateResponse ? "Re-analyze" : `Analyze ${league} Slate`}
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-400 text-sm mb-4">
            {error}
          </div>
        )}

        {loading ? (
          <SlateTableSkeleton />
        ) : slateResponse ? (
          <SlateTable analyses={filteredAnalyses} onRowClick={handleRowClick} />
        ) : (
          <div className="text-center text-gray-600 py-20 space-y-3">
            <p className="text-lg">No slate loaded</p>
            <p className="text-sm">
              Click &ldquo;Analyze {league} Slate&rdquo; to fetch and analyze today&apos;s games.
            </p>
          </div>
        )}
      </main>

      {/* Chat panel */}
      <ChatPanel context={chatContext} />
    </div>
  );
}
