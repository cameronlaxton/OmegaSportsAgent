"use client";

interface DotProps {
  score: number;
}

function qualityColor(score: number): string {
  if (score >= 0.7) return "bg-green-400";
  if (score >= 0.4) return "bg-yellow-400";
  return "bg-red-400";
}

function qualityLabel(score: number): string {
  if (score >= 0.7) return "Good";
  if (score >= 0.4) return "Fair";
  return "Poor";
}

/** Small colored dot for table rows. */
export function DataQualityDot({ score }: DotProps) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${qualityColor(score)}`}
      title={`Data quality: ${(score * 100).toFixed(0)}% (${qualityLabel(score)})`}
    />
  );
}

interface BadgeProps {
  score: number;
}

/** Pill badge for headers and detail pages. */
export function DataQualityBadge({ score }: BadgeProps) {
  const colorClasses =
    score >= 0.7
      ? "bg-green-500/20 text-green-400"
      : score >= 0.4
        ? "bg-yellow-500/20 text-yellow-400"
        : "bg-red-500/20 text-red-400";

  return (
    <span
      className={`text-xs font-bold px-2 py-0.5 rounded-full ${colorClasses}`}
      title={`Data quality: ${qualityLabel(score)}`}
    >
      DQ: {(score * 100).toFixed(0)}%
    </span>
  );
}
