"use client";

import { useState } from "react";
import { QueryInput } from "@/components/QueryInput";
import { MatchupCard } from "@/components/MatchupCard";
import type { GameAnalysisResponse } from "@/types/schemas";
import { analyzeGame } from "@/lib/api";

export default function Home() {
  const [analyses, setAnalyses] = useState<GameAnalysisResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleQuery(query: string) {
    setLoading(true);
    setError(null);

    try {
      // Parse query into request (simple heuristic — matches agent/orchestrator.py logic)
      const { home, away, league } = parseQuery(query);
      const result = await analyzeGame({
        home_team: home,
        away_team: away,
        league,
      });
      setAnalyses((prev) => [result, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">
          <span className="text-green-400">Omega</span>SportsAgent
        </h1>
        <p className="text-gray-500 text-sm">
          Quantitative edge detection &middot; Monte Carlo simulation &middot;
          Kelly staking
        </p>
      </div>

      {/* Query input */}
      <QueryInput onSubmit={handleQuery} loading={loading} />

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      <div className="space-y-6">
        {analyses.map((a, i) => (
          <MatchupCard key={`${a.matchup}-${i}`} analysis={a} />
        ))}
      </div>

      {/* Empty state */}
      {analyses.length === 0 && !loading && (
        <div className="text-center text-gray-600 py-16 space-y-3">
          <p className="text-lg">No analyses yet</p>
          <p className="text-sm">
            Try: &ldquo;Lakers vs Warriors NBA&rdquo; or &ldquo;Chiefs vs Bills
            NFL&rdquo;
          </p>
        </div>
      )}
    </main>
  );
}

/** Minimal client-side query parser. */
function parseQuery(query: string): {
  home: string;
  away: string;
  league: string;
} {
  const q = query.trim();
  const leagueMatch = q.match(
    /\b(NBA|NFL|MLB|NHL|EPL|UFC|ATP|PGA|CS2|NCAAB|NCAAF|MLS)\b/i,
  );
  const league = leagueMatch ? leagueMatch[1].toUpperCase() : "NBA";

  // Remove league from string for team extraction
  const cleaned = q.replace(
    /\b(NBA|NFL|MLB|NHL|EPL|UFC|ATP|PGA|CS2|NCAAB|NCAAF|MLS)\b/gi,
    "",
  );

  // Try "X vs Y" or "X at Y"
  const vsMatch = cleaned.match(/(.+?)\s+(?:vs\.?|versus|v\.?|at|@)\s+(.+)/i);
  if (vsMatch) {
    return {
      away: vsMatch[1].trim(),
      home: vsMatch[2].trim(),
      league,
    };
  }

  // Fallback: split on whitespace and take first two words
  const parts = cleaned.trim().split(/\s+/);
  return {
    away: parts[0] ?? "Team A",
    home: parts[1] ?? "Team B",
    league,
  };
}
