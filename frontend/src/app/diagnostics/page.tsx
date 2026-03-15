"use client";

import { useEffect, useState } from "react";
import { healthCheck } from "@/lib/api";

interface HealthStatus {
  status: string;
  engine?: string;
  version?: string;
}

interface ErrorEntry {
  timestamp: string;
  error_code: string;
  message: string;
}

export default function DiagnosticsPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [errors] = useState<ErrorEntry[]>([]);

  useEffect(() => {
    healthCheck()
      .then((r) => setHealth(r as unknown as HealthStatus))
      .catch((e) => setHealthError(e instanceof Error ? e.message : "Failed to reach backend"));
  }, []);

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-white mb-6">Diagnostics</h1>

      {/* Health check */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          System Health
        </h2>
        <div className="bg-gray-800/60 rounded-xl p-4 border border-gray-700/50">
          {healthError ? (
            <div className="flex items-center gap-3">
              <span className="w-3 h-3 rounded-full bg-red-400" />
              <span className="text-red-400 font-medium">Unreachable</span>
              <span className="text-gray-500 text-sm ml-2">{healthError}</span>
            </div>
          ) : health ? (
            <div className="flex items-center gap-3">
              <span
                className={`w-3 h-3 rounded-full ${
                  health.status === "ok" ? "bg-green-400" : "bg-yellow-400"
                }`}
              />
              <span className="text-white font-medium capitalize">{health.status}</span>
              {health.engine && (
                <span className="text-gray-500 text-sm">
                  {health.engine} v{health.version}
                </span>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <span className="w-3 h-3 rounded-full bg-gray-600 animate-pulse" />
              <span className="text-gray-400">Checking...</span>
            </div>
          )}
        </div>
      </section>

      {/* Recent errors */}
      <section>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Recent Errors
        </h2>
        {errors.length === 0 ? (
          <div className="text-gray-600 text-sm py-8 text-center">
            No errors recorded this session.
          </div>
        ) : (
          <div className="space-y-2">
            {errors.map((err, i) => (
              <div
                key={i}
                className="bg-gray-800/60 rounded-lg p-3 border border-gray-700/50 text-sm"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-red-400 font-mono text-xs">{err.error_code}</span>
                  <span className="text-gray-500 text-xs">{err.timestamp}</span>
                </div>
                <p className="text-gray-300">{err.message}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
