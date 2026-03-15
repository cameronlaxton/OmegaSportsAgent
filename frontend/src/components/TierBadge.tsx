"use client";

const TIER_COLORS: Record<string, string> = {
  A: "bg-green-500/20 text-green-400",
  B: "bg-yellow-500/20 text-yellow-400",
  C: "bg-orange-500/20 text-orange-400",
  Pass: "bg-gray-600/20 text-gray-500",
};

interface Props {
  tier: string;
  size?: "sm" | "md";
}

export function TierBadge({ tier, size = "sm" }: Props) {
  const sizeClasses = size === "md" ? "text-sm px-2.5 py-1" : "text-xs px-2 py-0.5";
  return (
    <span
      className={`font-bold rounded-full inline-block ${sizeClasses} ${TIER_COLORS[tier] ?? TIER_COLORS.Pass}`}
    >
      {tier}
    </span>
  );
}
