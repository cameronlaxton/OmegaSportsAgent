"use client";

import { useState } from "react";
import type { GameAnalysisResponse } from "@/types/schemas";
import { EdgeTable } from "@/components/EdgeTable";
import { DataQualityDot } from "@/components/DataQualityIndicator";

type Tab = "edges" | "reasoning" | "data" | "raw";

const TABS: { id: Tab; label: string }[] = [
  { id: "edges", label: "Edges" },
  { id: "reasoning", label: "Reasoning" },
  { id: "data", label: "Data & Provenance" },
  { id: "raw", label: "Raw" },
];

interface Props {
  analysis: GameAnalysisResponse;
  narratives?: {
    breakdown?: string;
    keyFactors?: string[];
    riskFactors?: string[];
  };
  dataQuality?: number;
  dataCompleteness?: Record<string, string>;
}

export function AnalysisTabs({
  analysis,
  narratives,
  dataQuality,
  dataCompleteness,
}: Props) {
  const [active, setActive] = useState<Tab>("edges");

  return (
    <div>
      {/* Tab bar */}
      <div className="flex border-b border-gray-700 mb-4">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors relative ${
              active === tab.id
                ? "text-green-400"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {tab.label}
            {active === tab.id && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-green-400" />
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {active === "edges" && <EdgesTab analysis={analysis} />}
      {active === "reasoning" && <ReasoningTab narratives={narratives} />}
      {active === "data" && (
        <DataTab
          analysis={analysis}
          dataQuality={dataQuality}
          dataCompleteness={dataCompleteness}
        />
      )}
      {active === "raw" && <RawTab analysis={analysis} />}
    </div>
  );
}

function EdgesTab({ analysis }: { analysis: GameAnalysisResponse }) {
  if (!analysis.edges || analysis.edges.length === 0) {
    return <p className="text-gray-500 text-sm py-4">No edges detected.</p>;
  }
  return <EdgeTable edges={analysis.edges} />;
}

function ReasoningTab({
  narratives,
}: {
  narratives?: Props["narratives"];
}) {
  if (!narratives) {
    return (
      <p className="text-gray-500 text-sm py-4">
        No narrative reasoning available for this analysis.
      </p>
    );
  }

  return (
    <div className="space-y-6 text-sm">
      {narratives.breakdown && (
        <div>
          <h3 className="text-white font-semibold mb-2">Game Breakdown</h3>
          <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">
            {narratives.breakdown}
          </p>
        </div>
      )}
      {narratives.keyFactors && narratives.keyFactors.length > 0 && (
        <div>
          <h3 className="text-white font-semibold mb-2">Key Factors</h3>
          <ul className="list-disc list-inside space-y-1 text-gray-300">
            {narratives.keyFactors.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}
      {narratives.riskFactors && narratives.riskFactors.length > 0 && (
        <div>
          <h3 className="text-white font-semibold mb-2">Risk Factors</h3>
          <ul className="list-disc list-inside space-y-1 text-yellow-400/80">
            {narratives.riskFactors.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function DataTab({
  analysis,
  dataQuality,
  dataCompleteness,
}: {
  analysis: GameAnalysisResponse;
  dataQuality?: number;
  dataCompleteness?: Record<string, string>;
}) {
  const dq = dataQuality ?? 0.5;

  return (
    <div className="space-y-6">
      {/* Quality score */}
      <div>
        <h3 className="text-white font-semibold text-sm mb-2">Data Quality</h3>
        <div className="flex items-center gap-4">
          <span className="text-3xl font-mono font-bold text-white">
            {(dq * 100).toFixed(0)}%
          </span>
          <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                dq >= 0.7 ? "bg-green-400" : dq >= 0.4 ? "bg-yellow-400" : "bg-red-400"
              }`}
              style={{ width: `${dq * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Completeness */}
      {dataCompleteness && Object.keys(dataCompleteness).length > 0 && (
        <div>
          <h3 className="text-white font-semibold text-sm mb-2">Data Completeness</h3>
          <div className="bg-gray-800/40 rounded-xl p-3">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 uppercase tracking-wider">
                  <th className="text-left py-1">Slot</th>
                  <th className="text-center py-1 w-16">Status</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(dataCompleteness).map(([key, status]) => (
                  <tr key={key} className="border-t border-gray-800/40">
                    <td className="py-1.5 text-gray-300 font-mono">{key}</td>
                    <td className="py-1.5 text-center">
                      <DataQualityDot
                        score={status === "real" ? 1 : status === "defaulted" ? 0.5 : 0}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sources */}
      {analysis.metadata.data_sources.length > 0 && (
        <div>
          <h3 className="text-white font-semibold text-sm mb-2">Sources</h3>
          <div className="flex flex-wrap gap-1.5">
            {analysis.metadata.data_sources.map((s) => (
              <span
                key={s}
                className="px-2 py-0.5 bg-gray-800 text-gray-400 text-xs rounded"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Metadata */}
      <div>
        <h3 className="text-white font-semibold text-sm mb-2">Analysis Metadata</h3>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <MetaItem label="Engine" value={analysis.metadata.engine_version} />
          <MetaItem label="Calibration" value={analysis.metadata.calibration_method} />
          <MetaItem label="Archetype" value={analysis.metadata.archetype ?? "N/A"} />
          <MetaItem
            label="Iterations"
            value={analysis.simulation?.iterations.toLocaleString() ?? "N/A"}
          />
          <MetaItem
            label="Analyzed"
            value={new Date(analysis.analyzed_at).toLocaleString()}
          />
        </div>
      </div>
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-gray-500 uppercase">{label}</span>
      <p className="text-gray-300 font-mono mt-0.5">{value}</p>
    </div>
  );
}

function RawTab({ analysis }: { analysis: GameAnalysisResponse }) {
  return (
    <pre className="bg-gray-900 p-4 rounded-xl text-xs font-mono text-gray-400 overflow-auto max-h-[600px]">
      {JSON.stringify(analysis, null, 2)}
    </pre>
  );
}
