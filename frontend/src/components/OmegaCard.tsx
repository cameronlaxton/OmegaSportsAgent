"use client";

/**
 * OmegaCard — rich visual game analysis card inspired by the Omega "card + ticket" format.
 *
 * Displays: market snapshot, simulation probabilities with visual bars,
 * edge table, and recommended bets with confidence tiers.
 */

interface OmegaEdge {
  side?: string;
  team?: string;
  selection?: string;
  true_prob?: number;
  calibrated_prob?: number;
  market_implied?: number;
  edge_pct?: number;
  ev_pct?: number;
  market_odds?: number;
  confidence_tier?: string;
  recommended_units?: number;
  kelly_fraction?: number;
}

interface OmegaSimulation {
  iterations?: number;
  home_win_prob?: number;
  away_win_prob?: number;
  predicted_spread?: number;
  predicted_total?: number;
  predicted_home_score?: number;
  predicted_away_score?: number;
}

interface OmegaBestBet {
  selection?: string;
  odds?: number;
  edge_pct?: number;
  ev_pct?: number;
  confidence_tier?: string;
  recommended_units?: number;
  kelly_fraction?: number;
}

interface Props {
  matchup?: string;
  league?: string;
  simulation?: OmegaSimulation | null;
  edges?: OmegaEdge[];
  bestBet?: OmegaBestBet | null;
  dataQuality?: number;
  narrative?: string;
}

function ProbBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-gray-400 w-24 shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] font-mono text-gray-300 w-12 text-right">
        {(pct).toFixed(1)}%
      </span>
    </div>
  );
}

function TierBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    A: "bg-green-500/20 text-green-400 border-green-500/30",
    B: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    C: "bg-gray-500/20 text-gray-400 border-gray-500/30",
    Pass: "bg-red-500/20 text-red-400 border-red-500/30",
  };
  return (
    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded border ${colors[tier] ?? colors.C}`}>
      {tier}
    </span>
  );
}

function formatOdds(odds: number): string {
  if (odds >= 0) return `+${odds}`;
  return `${odds}`;
}

export function OmegaCard({ matchup, league, simulation, edges, bestBet, dataQuality, narrative }: Props) {
  const hasEdges = edges && edges.length > 0;
  const hasSim = simulation && (simulation.home_win_prob || simulation.away_win_prob);

  return (
    <div className="rounded-xl border border-gray-700/40 bg-gray-900/80 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700/30 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            {league && (
              <span className="text-[10px] font-semibold uppercase tracking-wider text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded">
                {league}
              </span>
            )}
            {dataQuality != null && dataQuality > 0 && (
              <span className="text-[10px] text-gray-500">
                {(dataQuality * 100).toFixed(0)}% data
              </span>
            )}
          </div>
          {matchup && (
            <h3 className="text-base font-bold text-white mt-1">{matchup}</h3>
          )}
        </div>
        {hasSim && simulation?.iterations && (
          <span className="text-[10px] text-gray-500">
            {simulation.iterations.toLocaleString()} sims
          </span>
        )}
      </div>

      {/* Simulation probabilities */}
      {hasSim && (
        <div className="px-4 py-3 border-b border-gray-700/20 space-y-1.5">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-2">
            Simulation
          </p>
          {simulation!.home_win_prob != null && (
            <ProbBar label="Home Win" value={simulation!.home_win_prob} color="bg-blue-500" />
          )}
          {simulation!.away_win_prob != null && (
            <ProbBar label="Away Win" value={simulation!.away_win_prob} color="bg-green-500" />
          )}
          {simulation!.predicted_spread != null && (
            <div className="flex gap-4 mt-2 text-[11px] text-gray-400">
              <span>Spread: <span className="text-white font-mono">{simulation!.predicted_spread > 0 ? "+" : ""}{simulation!.predicted_spread.toFixed(1)}</span></span>
              {simulation!.predicted_total != null && (
                <span>Total: <span className="text-white font-mono">{simulation!.predicted_total.toFixed(1)}</span></span>
              )}
              {simulation!.predicted_home_score != null && simulation!.predicted_away_score != null && (
                <span>Score: <span className="text-white font-mono">{simulation!.predicted_home_score.toFixed(0)}-{simulation!.predicted_away_score.toFixed(0)}</span></span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Edge table */}
      {hasEdges && (
        <div className="px-4 py-3 border-b border-gray-700/20">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-2">
            Edges
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="text-left py-1 pr-2 font-medium">Selection</th>
                  <th className="text-right py-1 px-2 font-medium">True</th>
                  <th className="text-right py-1 px-2 font-medium">Impl</th>
                  <th className="text-right py-1 px-2 font-medium">Edge</th>
                  <th className="text-right py-1 px-2 font-medium">Kelly</th>
                  <th className="text-center py-1 pl-2 font-medium">Tier</th>
                </tr>
              </thead>
              <tbody>
                {edges!.map((e, i) => {
                  const edgePct = e.edge_pct ?? 0;
                  const edgeColor = edgePct > 3 ? "text-green-400" : edgePct > 0 ? "text-yellow-400" : "text-gray-400";
                  return (
                    <tr key={i} className="border-b border-gray-800/50">
                      <td className="py-1.5 pr-2 text-white font-medium">
                        {e.selection ?? e.team ?? e.side ?? "—"}
                        {e.market_odds != null && (
                          <span className="text-gray-500 ml-1 font-mono text-[10px]">
                            ({formatOdds(e.market_odds)})
                          </span>
                        )}
                      </td>
                      <td className="py-1.5 px-2 text-right font-mono text-gray-300">
                        {e.true_prob != null ? `${(e.true_prob * 100).toFixed(1)}%` : "—"}
                      </td>
                      <td className="py-1.5 px-2 text-right font-mono text-gray-500">
                        {e.market_implied != null ? `${(e.market_implied * 100).toFixed(1)}%` : "—"}
                      </td>
                      <td className={`py-1.5 px-2 text-right font-mono font-semibold ${edgeColor}`}>
                        {edgePct > 0 ? "+" : ""}{edgePct.toFixed(1)}%
                      </td>
                      <td className="py-1.5 px-2 text-right font-mono text-gray-400">
                        {e.kelly_fraction != null ? `${(e.kelly_fraction * 100).toFixed(1)}%` :
                         e.recommended_units != null ? `${e.recommended_units.toFixed(1)}u` : "—"}
                      </td>
                      <td className="py-1.5 pl-2 text-center">
                        <TierBadge tier={e.confidence_tier ?? "C"} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Best bet / recommended */}
      {bestBet && (
        <div className="px-4 py-3 border-b border-gray-700/20">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-2">
            Top Play
          </p>
          <div className="flex items-center gap-3 bg-green-500/5 border border-green-500/20 rounded-lg px-3 py-2">
            <TierBadge tier={bestBet.confidence_tier ?? "B"} />
            <div className="flex-1">
              <span className="text-sm font-semibold text-white">{bestBet.selection}</span>
              {bestBet.odds != null && (
                <span className="text-gray-400 text-xs ml-2">({formatOdds(bestBet.odds)})</span>
              )}
            </div>
            <div className="text-right">
              {bestBet.edge_pct != null && (
                <div className="text-xs font-mono text-green-400">+{bestBet.edge_pct.toFixed(1)}% edge</div>
              )}
              {bestBet.recommended_units != null && (
                <div className="text-[10px] text-gray-500">{bestBet.recommended_units.toFixed(1)}u stake</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Narrative */}
      {narrative && (
        <div className="px-4 py-3 text-xs text-gray-400 leading-relaxed">
          {narrative}
        </div>
      )}
    </div>
  );
}
