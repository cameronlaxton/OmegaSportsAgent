/** API client for the OmegaSportsAgent backend. */

import type {
  ChatStreamEvent,
  GameAnalysisResponse,
  SlateAnalysisResponse,
} from "@/types/schemas";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message ?? `API error ${res.status}`);
  }
  return res.json();
}

export async function analyzeGame(req: {
  home_team: string;
  away_team: string;
  league: string;
  odds?: {
    spread_home?: number;
    spread_home_price?: number;
    moneyline_home?: number;
    moneyline_away?: number;
    over_under?: number;
  };
}): Promise<GameAnalysisResponse> {
  return post("/api/analyze/game", req);
}

export async function analyzeSlate(req: {
  league: string;
  date?: string;
  bankroll?: number;
  games?: unknown[];
}): Promise<SlateAnalysisResponse> {
  return post("/api/analyze/slate", req);
}

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/health`);
  return res.json();
}

/**
 * Stream a chat message to the backend via SSE.
 *
 * Returns an AbortController so the caller can cancel the stream.
 */
export function chatStream(
  message: string,
  sessionId: string | null,
  onEvent: (event: ChatStreamEvent) => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, session_id: sessionId }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        onEvent({
          event_type: "error",
          data: { message: `HTTP ${res.status}: ${res.statusText}` },
          session_id: sessionId ?? "",
        });
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const parsed = JSON.parse(line.slice(6)) as ChatStreamEvent;
              onEvent(parsed);
            } catch {
              // skip malformed events
            }
          }
        }
      }

      // Process any remaining data in buffer
      if (buffer.startsWith("data: ")) {
        try {
          const parsed = JSON.parse(buffer.slice(6)) as ChatStreamEvent;
          onEvent(parsed);
        } catch {
          // skip
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        onEvent({
          event_type: "error",
          data: { message: (err as Error).message },
          session_id: sessionId ?? "",
        });
      }
    }
  })();

  return controller;
}
