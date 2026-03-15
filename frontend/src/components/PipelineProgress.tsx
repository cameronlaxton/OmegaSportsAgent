"use client";

const STAGES = [
  { key: "intent_understanding", label: "Intent" },
  { key: "answer_strategy", label: "Strategy" },
  { key: "requirement_planning", label: "Planning" },
  { key: "fact_gathering", label: "Data" },
  { key: "quality_gate", label: "Quality" },
  { key: "execution", label: "Simulation" },
  { key: "response_composition", label: "Composing" },
];

interface Props {
  currentStage: string | null;
}

export function PipelineProgress({ currentStage }: Props) {
  if (!currentStage) return null;

  const currentIndex = STAGES.findIndex((s) => s.key === currentStage);

  return (
    <div className="flex items-center gap-1 px-3 py-2 bg-gray-800/60 rounded-lg text-xs">
      {STAGES.map((stage, i) => {
        const isActive = stage.key === currentStage;
        const isDone = i < currentIndex;

        return (
          <div key={stage.key} className="flex items-center gap-1">
            {i > 0 && (
              <div
                className={`w-4 h-px ${isDone ? "bg-green-500" : "bg-gray-700"}`}
              />
            )}
            <span
              className={`px-2 py-0.5 rounded ${
                isActive
                  ? "bg-green-600/30 text-green-400 font-medium"
                  : isDone
                    ? "text-green-500/70"
                    : "text-gray-600"
              }`}
            >
              {stage.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
