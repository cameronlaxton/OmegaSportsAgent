"use client";

import type { ChatMessage as ChatMessageType } from "@/types/schemas";
import { MatchupCard } from "./MatchupCard";
import type { GameAnalysisResponse } from "@/types/schemas";

interface Props {
  message: ChatMessageType;
}

export function ChatMessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  // Try to render structured data as a MatchupCard if it looks like a game analysis
  const structuredData = message.structured_data;
  const hasSimulation =
    structuredData &&
    structuredData.type === "answer" &&
    Array.isArray(structuredData.sections);

  // Extract game analysis from structured data sections if present
  let gameAnalysis: GameAnalysisResponse | null = null;
  if (hasSimulation) {
    const sections = structuredData.sections as Array<Record<string, unknown>>;
    for (const section of sections) {
      if (section.simulation && section.package === "game_breakdown") {
        // Build a GameAnalysisResponse-like object from structured data
        const metadata = structuredData.metadata as Record<string, unknown> | undefined;
        gameAnalysis = {
          matchup: "Analysis",
          league: "",
          analyzed_at: message.timestamp ?? new Date().toISOString(),
          status: "success" as const,
          skip_reason: null,
          missing_requirements: null,
          simulation: section.simulation as GameAnalysisResponse["simulation"],
          edges: (structuredData.sections as Array<Record<string, unknown>>)
            .find((s) => s.package === "bet_card")
            ?.edges as GameAnalysisResponse["edges"] ?? [],
          best_bet: (structuredData.sections as Array<Record<string, unknown>>)
            .find((s) => s.package === "bet_card")
            ?.best_bet as GameAnalysisResponse["best_bet"] ?? null,
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

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-green-600/20 border border-green-600/30 text-white"
            : "bg-gray-800/80 border border-gray-700 text-gray-200"
        }`}
      >
        {/* Text content */}
        {message.content && (
          <div className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </div>
        )}

        {/* Structured game analysis card */}
        {gameAnalysis && (
          <div className="mt-3">
            <MatchupCard analysis={gameAnalysis} />
          </div>
        )}

        {/* Timestamp */}
        {message.timestamp && (
          <div className="mt-1 text-[10px] text-gray-500">
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
}
