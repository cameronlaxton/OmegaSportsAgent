"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { chatStream } from "@/lib/api";
import type { ChatMessage, ChatStreamEvent } from "@/types/schemas";
import { ChatMessageBubble } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { PipelineProgress } from "./PipelineProgress";

export function ChatContainer() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, currentStage]);

  const handleSend = useCallback(
    (text: string) => {
      setError(null);
      setIsStreaming(true);
      setCurrentStage(null);

      const userMessage: ChatMessage = {
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Accumulate narrative text for the assistant message
      let narrativeText = "";
      let structuredData: Record<string, unknown> | null = null;
      let resolvedSessionId = sessionId;

      const controller = chatStream(text, sessionId, (event: ChatStreamEvent) => {
        switch (event.event_type) {
          case "stage_update":
            setCurrentStage(event.data as string);
            break;

          case "partial_text":
            narrativeText = event.data as string;
            // Update the assistant message in progress
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant") {
                return [
                  ...prev.slice(0, -1),
                  { ...last, content: narrativeText },
                ];
              }
              return [
                ...prev,
                {
                  role: "assistant" as const,
                  content: narrativeText,
                  timestamp: new Date().toISOString(),
                  structured_data: structuredData,
                },
              ];
            });
            break;

          case "structured_data":
            structuredData = event.data as Record<string, unknown>;
            // Add or update assistant message with structured data
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant") {
                return [
                  ...prev.slice(0, -1),
                  { ...last, structured_data: structuredData },
                ];
              }
              return [
                ...prev,
                {
                  role: "assistant" as const,
                  content: narrativeText,
                  timestamp: new Date().toISOString(),
                  structured_data: structuredData,
                },
              ];
            });
            break;

          case "suggested_followups": {
            const followupList = event.data as string[];
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant") {
                return [...prev.slice(0, -1), { ...last, suggested_followups: followupList }];
              }
              return prev;
            });
            break;
          }

          case "done": {
            const doneData = event.data as { session_id?: string };
            if (doneData?.session_id) {
              resolvedSessionId = doneData.session_id;
              setSessionId(doneData.session_id);
            }
            setIsStreaming(false);
            setCurrentStage(null);

            // Ensure there's an assistant message even if no narrative was streamed
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role !== "assistant") {
                return [
                  ...prev,
                  {
                    role: "assistant" as const,
                    content: narrativeText || "Analysis complete.",
                    timestamp: new Date().toISOString(),
                    structured_data: structuredData,
                  },
                ];
              }
              return prev;
            });
            break;
          }

          case "error":
            setIsStreaming(false);
            setCurrentStage(null);
            setError((event.data as { message?: string })?.message ?? "Unknown error");
            break;
        }
      });

      abortRef.current = controller;
    },
    [sessionId],
  );

  return (
    <div className="flex flex-col h-[calc(100vh-180px)] max-w-4xl mx-auto">
      {/* Messages area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-4 px-2 py-4"
      >
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-20 space-y-4">
            <p className="text-lg">Ask about any sports matchup</p>
            <div className="flex flex-wrap justify-center gap-2 text-sm">
              {[
                "Who has an edge in Lakers vs Warriors tonight?",
                "Break down Chiefs vs Bills NFL",
                "Any value on the NBA slate today?",
                "LeBron over 25.5 points — worth a play?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => handleSend(suggestion)}
                  className="px-3 py-1.5 bg-gray-800/60 border border-gray-700 rounded-lg hover:border-green-600/50 hover:text-green-400 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessageBubble key={i} message={msg} onFollowup={handleSend} />
        ))}

        {/* Pipeline progress during streaming */}
        {isStreaming && currentStage && (
          <div className="flex justify-start">
            <PipelineProgress currentStage={currentStage} />
          </div>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className="mx-2 mb-2 px-4 py-2 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Input area */}
      <div className="px-2 py-3 border-t border-gray-800">
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
