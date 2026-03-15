"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { chatStream } from "@/lib/api";
import type { ChatMessage, ChatStreamEvent } from "@/types/schemas";
import { ChatMessageBubble } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { PipelineProgress } from "./PipelineProgress";

interface Props {
  /** Optional context to display as a chip above the input. */
  context?: string | null;
}

export function ChatPanel({ context }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, currentStage]);

  const handleSend = useCallback(
    (text: string) => {
      // Prepend context if available and user message doesn't reference it
      const contextPrefix = context ? `[Context: ${context}] ` : "";
      const fullMessage = contextPrefix + text;

      setError(null);
      setIsStreaming(true);
      setCurrentStage(null);

      const userMessage: ChatMessage = {
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      let narrativeText = "";
      let structuredData: Record<string, unknown> | null = null;

      const controller = chatStream(fullMessage, sessionId, (event: ChatStreamEvent) => {
        switch (event.event_type) {
          case "stage_update":
            setCurrentStage(event.data as string);
            break;

          case "partial_text":
            narrativeText = event.data as string;
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant") {
                return [...prev.slice(0, -1), { ...last, content: narrativeText }];
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
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant") {
                return [...prev.slice(0, -1), { ...last, structured_data: structuredData }];
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

          case "done": {
            const doneData = event.data as { session_id?: string };
            if (doneData?.session_id) {
              setSessionId(doneData.session_id);
            }
            setIsStreaming(false);
            setCurrentStage(null);
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
    [sessionId, context],
  );

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="fixed bottom-6 right-6 w-12 h-12 bg-green-600 hover:bg-green-500 rounded-full flex items-center justify-center shadow-lg transition-colors z-50"
        title="Open chat"
      >
        <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </button>
    );
  }

  return (
    <div className="w-[380px] bg-gray-900 border-l border-gray-800 flex flex-col shrink-0">
      {/* Header */}
      <div className="h-10 flex items-center justify-between px-3 border-b border-gray-800 shrink-0">
        <span className="text-sm text-gray-400 font-medium">Assistant</span>
        <button
          onClick={() => setCollapsed(true)}
          className="text-gray-500 hover:text-gray-300 transition-colors p-1"
          title="Collapse chat"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-3 px-3 py-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-600 mt-12 space-y-3">
            <p className="text-sm">Ask about any matchup or edge</p>
            <div className="flex flex-col gap-1.5 text-xs">
              {[
                "Any value on the NBA slate?",
                "Break down Lakers vs Warriors",
                "LeBron over 25.5 points?",
              ].map((s) => (
                <button
                  key={s}
                  onClick={() => handleSend(s)}
                  className="px-3 py-1.5 bg-gray-800/60 border border-gray-700 rounded-lg hover:border-green-600/50 hover:text-green-400 transition-colors text-gray-400"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessageBubble key={i} message={msg} />
        ))}

        {isStreaming && currentStage && (
          <div className="flex justify-start">
            <PipelineProgress currentStage={currentStage} />
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mx-3 mb-2 px-3 py-2 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-xs">
          {error}
        </div>
      )}

      {/* Context chip */}
      {context && (
        <div className="mx-3 mb-1">
          <span className="inline-block px-2 py-0.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-400">
            Viewing: {context}
          </span>
        </div>
      )}

      {/* Input */}
      <div className="px-3 py-2 border-t border-gray-800 shrink-0">
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
