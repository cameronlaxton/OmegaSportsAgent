"use client";

import type { GameAnalysisResponse } from "@/types/schemas";
import { ProbabilityBar } from "./ProbabilityBar";
import { EdgeTable } from "./EdgeTable";
import { BetSlipCard } from "./BetSlipCard";

interface Props {
  analysis: GameAnalysisResponse;
}

export function MatchupCard({ analysis }: Props) {
  const { matchup, league, status, simulation, edges, best_bet, metadata } =
    analysis;

  const statusColor =
    status === "success"
      ? "border-green-500/30"
      : status === "skipped"
        ? "border-yellow-500/30"
        : "border-red-500/30";

  return (
    <div
      className={`rounded-2xl border ${statusColor} bg-gray-900/80 backdrop-blur-sm p-6 space-y-5`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">{matchup}</h2>
          <p className="text-sm text-gray-400">
            {league} &middot; {metadata?.archetype ?? "simulation"} &middot;{" "}
            {simulation?.iterations?.toLocaleString() ?? 0} iterations
          </p>
        </div>
        <span
          className={`text-xs font-semibold uppercase px-3 py-1 rounded-full ${
            status === "success"
              ? "bg-green-500/20 text-green-400"
              : status === "skipped"
                ? "bg-yellow-500/20 text-yellow-400"
                : "bg-red-500/20 text-red-400"
          }`}
        >
          {status}
        </span>
      </div>

      {/* Skip / error message */}
      {analysis.skip_reason && (
        <p className="text-sm text-yellow-300/80 bg-yellow-500/10 rounded-lg p-3">
          {analysis.skip_reason}
        </p>
      )}

      {/* Simulation results */}
      {simulation && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <Stat label="Predicted Spread" value={fmtSpread(simulation.predicted_spread)} />
          <Stat label="Predicted Total" value={simulation.predicted_total.toFixed(1)} />
          <Stat
            label="Home Score"
            value={simulation.predicted_home_score.toFixed(1)}
          />
          <Stat
            label="Away Score"
            value={simulation.predicted_away_score.toFixed(1)}
          />
        </div>
      )}

      {/* Probability bar */}
      {simulation && (
        <ProbabilityBar
          homeProb={simulation.home_win_prob}
          awayProb={simulation.away_win_prob}
          drawProb={simulation.draw_prob}
          homeTeam={matchup.split(" @ ")[1] ?? "Home"}
          awayTeam={matchup.split(" @ ")[0] ?? "Away"}
        />
      )}

      {/* Edge table */}
      {edges.length > 0 && <EdgeTable edges={edges} />}

      {/* Best bet */}
      {best_bet && <BetSlipCard slip={best_bet} />}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800/60 rounded-xl p-3">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-lg font-mono font-bold text-white mt-1">{value}</p>
    </div>
  );
}

function fmtSpread(n: number): string {
  return n > 0 ? `+${n.toFixed(1)}` : n.toFixed(1);
}
