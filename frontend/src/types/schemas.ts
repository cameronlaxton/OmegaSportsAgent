/** Mirrors src/contracts/schemas.py — the JSON contract between backend and frontend. */

export interface SimulationResult {
  iterations: number;
  home_win_prob: number;
  away_win_prob: number;
  draw_prob: number | null;
  predicted_spread: number;
  predicted_total: number;
  predicted_home_score: number;
  predicted_away_score: number;
}

export interface EdgeDetail {
  side: "home" | "away" | "draw";
  team: string;
  true_prob: number;
  calibrated_prob: number;
  market_implied: number;
  edge_pct: number;
  ev_pct: number;
  market_odds: number;
  confidence_tier: "A" | "B" | "C" | "Pass";
}

export interface BetSlip {
  selection: string;
  odds: number;
  edge_pct: number;
  ev_pct: number;
  confidence_tier: string;
  recommended_units: number;
  kelly_fraction: number;
}

export interface AnalysisMetadata {
  engine_version: string;
  calibration_method: string;
  data_sources: string[];
  archetype: string | null;
}

export interface GameAnalysisResponse {
  matchup: string;
  league: string;
  analyzed_at: string;
  status: "success" | "skipped" | "error";
  skip_reason: string | null;
  missing_requirements: string[] | null;
  simulation: SimulationResult | null;
  edges: EdgeDetail[];
  best_bet: BetSlip | null;
  metadata: AnalysisMetadata;
}

export interface SlateAnalysisResponse {
  league: string;
  date: string;
  total_games: number;
  games_analyzed: number;
  games_with_edge: number;
  analyses: GameAnalysisResponse[];
}

export interface PlayerPropResponse {
  player_name: string;
  league: string;
  prop_type: string;
  line: number;
  status: "success" | "skipped" | "error";
  over_prob: number | null;
  under_prob: number | null;
  edge_over: number | null;
  edge_under: number | null;
  recommendation: string | null;
  confidence_tier: "A" | "B" | "C" | "Pass";
}

export interface ErrorResponse {
  error_code: string;
  message: string;
  context: Record<string, unknown> | null;
  fallback_hint: string | null;
}

// -- Chat Types ---------------------------------------------------------------

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
  structured_data?: Record<string, unknown> | null;
  suggested_followups?: string[];
}

export type ChatEventType =
  | "stage_update"
  | "partial_text"
  | "structured_data"
  | "suggested_followups"
  | "done"
  | "error";

export interface ChatStreamEvent {
  event_type: ChatEventType;
  data: unknown;
  session_id: string;
}

export interface ChatState {
  messages: ChatMessage[];
  sessionId: string | null;
  isStreaming: boolean;
  currentStage: string | null;
}
