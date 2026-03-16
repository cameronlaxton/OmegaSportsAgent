"use client";

import type { ChatMessage as ChatMessageType } from "@/types/schemas";
import { MatchupCard } from "./MatchupCard";
import { OmegaCard } from "./OmegaCard";
import type { GameAnalysisResponse } from "@/types/schemas";
import ReactMarkdown from "react-markdown";

interface Props {
  message: ChatMessageType;
  onFollowup?: (text: string) => void;
}

export function ChatMessageBubble({ message, onFollowup }: Props) {
  const isUser = message.role === "user";

  // ---- Structured data parsing ----
  const structuredData = message.structured_data;
  const hasSections =
    structuredData &&
    structuredData.type === "answer" &&
    Array.isArray(structuredData.sections);

  // Try to build OmegaCard props from structured data
  let omegaCardProps: {
    matchup?: string;
    league?: string;
    simulation?: Record<string, unknown> | null;
    edges?: Record<string, unknown>[];
    bestBet?: Record<string, unknown> | null;
    dataQuality?: number;
    narrative?: string;
  } | null = null;

  let gameAnalysis: GameAnalysisResponse | null = null;

  if (hasSections) {
    const sections = structuredData.sections as Array<Record<string, unknown>>;
    const metadata = structuredData.metadata as Record<string, unknown> | undefined;

    // Look for game_breakdown or bet_card packages -> OmegaCard
    const gameSection = sections.find(
      (s) => s.package === "game_breakdown" || s.package === "compact_summary"
    );
    const betSection = sections.find((s) => s.package === "bet_card");

    if (gameSection || betSection) {
      omegaCardProps = {
        matchup: (metadata?.matchup as string) ?? (gameSection?.matchup as string) ?? "Analysis",
        league: (metadata?.league as string) ?? (gameSection?.league as string) ?? "",
        simulation: (gameSection?.simulation as Record<string, unknown>) ?? null,
        edges: (betSection?.edges as Record<string, unknown>[]) ?? [],
        bestBet: (betSection?.best_bet as Record<string, unknown>) ?? null,
        dataQuality: metadata?.data_quality as number | undefined,
        narrative: undefined,
      };
    }

    // Fallback: full GameAnalysisResponse for MatchupCard
    if (!omegaCardProps) {
      for (const section of sections) {
        if (section.simulation && section.package === "game_breakdown") {
          gameAnalysis = {
            matchup: "Analysis",
            league: "",
            analyzed_at: message.timestamp ?? new Date().toISOString(),
            status: "success" as const,
            skip_reason: null,
            missing_requirements: null,
            simulation: section.simulation as GameAnalysisResponse["simulation"],
            edges:
              (sections.find((s) => s.package === "bet_card")?.edges as GameAnalysisResponse["edges"]) ?? [],
            best_bet:
              (sections.find((s) => s.package === "bet_card")?.best_bet as GameAnalysisResponse["best_bet"]) ?? null,
            metadata: {
              engine_version: (metadata?.engine_version as string) ?? "2.0-dse",
              calibration_method: (metadata?.calibration_method as string) ?? "combined",
              data_sources: (metadata?.data_sources as string[]) ?? ["simulation"],
              archetype: (metadata?.archetype as string) ?? null,
            },
          };
          break;
        }
      }
    }
  }

  // Follow-up suggestions
  const followups = message.suggested_followups;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-message-in`}>
      <div
        className={`max-w-[90%] rounded-2xl px-5 py-3.5 ${
          isUser
            ? "bg-green-600/15 border border-green-600/25 text-white"
            : "bg-gray-800/50 border border-gray-700/40 text-gray-200"
        }`}
      >
        {/* Text content */}
        {message.content && (
          <div className={isUser ? "text-sm leading-relaxed" : ""}>
            {isUser ? (
              <span>{message.content}</span>
            ) : (
              <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-p:my-1.5 prose-headings:text-green-400 prose-strong:text-green-300 prose-code:text-green-300 prose-code:bg-gray-800 prose-code:px-1 prose-code:rounded prose-table:text-xs prose-th:text-gray-400 prose-th:border-gray-700 prose-td:border-gray-700/50">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            )}
          </div>
        )}

        {/* OmegaCard — rich game analysis card */}
        {omegaCardProps && (
          <div className="mt-3">
            <OmegaCard
              matchup={omegaCardProps.matchup}
              league={omegaCardProps.league}
              simulation={omegaCardProps.simulation as any}
              edges={omegaCardProps.edges as any}
              bestBet={omegaCardProps.bestBet as any}
              dataQuality={omegaCardProps.dataQuality}
              narrative={omegaCardProps.narrative}
            />
          </div>
        )}

        {/* MatchupCard fallback for full sim responses */}
        {!omegaCardProps && gameAnalysis && (
          <div className="mt-3">
            <MatchupCard analysis={gameAnalysis} />
          </div>
        )}

        {/* Timestamp */}
        {message.timestamp && (
          <div className="mt-2 text-[10px] text-gray-500/60">
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        )}

        {/* Follow-up suggestions */}
        {followups && followups.length > 0 && onFollowup && (
          <div className="mt-3 pt-2 border-t border-gray-700/30 flex flex-wrap gap-1.5">
            {followups.map((f, i) => (
              <button
                key={i}
                onClick={() => onFollowup(f)}
                className="px-2.5 py-1 text-[11px] bg-gray-700/30 border border-gray-600/30 rounded-full text-gray-400 hover:text-green-400 hover:border-green-600/40 transition-colors"
              >
                {f}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
