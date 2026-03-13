"use client";

interface Props {
  homeProb: number;
  awayProb: number;
  drawProb: number | null;
  homeTeam: string;
  awayTeam: string;
}

export function ProbabilityBar({
  homeProb,
  awayProb,
  drawProb,
  homeTeam,
  awayTeam,
}: Props) {
  const draw = drawProb ?? 0;
  const total = homeProb + awayProb + draw;
  const homePct = total > 0 ? (homeProb / total) * 100 : 50;
  const drawPct = total > 0 ? (draw / total) * 100 : 0;
  const awayPct = 100 - homePct - drawPct;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-gray-400">
        <span>
          {homeTeam}{" "}
          <span className="font-bold text-green-400">{homeProb.toFixed(1)}%</span>
        </span>
        {draw > 0 && (
          <span>
            Draw{" "}
            <span className="font-bold text-gray-300">{draw.toFixed(1)}%</span>
          </span>
        )}
        <span>
          <span className="font-bold text-blue-400">{awayProb.toFixed(1)}%</span>{" "}
          {awayTeam}
        </span>
      </div>

      <div className="flex h-3 rounded-full overflow-hidden bg-gray-800">
        <div
          className="bg-gradient-to-r from-green-600 to-green-500 transition-all duration-500"
          style={{ width: `${homePct}%` }}
        />
        {drawPct > 0 && (
          <div
            className="bg-gray-500 transition-all duration-500"
            style={{ width: `${drawPct}%` }}
          />
        )}
        <div
          className="bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500"
          style={{ width: `${awayPct}%` }}
        />
      </div>
    </div>
  );
}
