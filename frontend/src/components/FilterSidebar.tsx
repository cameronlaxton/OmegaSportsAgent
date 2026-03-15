"use client";

const LEAGUES = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "EPL", "UFC"] as const;
const DATE_OPTIONS = ["Yesterday", "Today", "Tomorrow"] as const;
const EDGE_FILTERS = ["All Games", "Edges Only", "Tier A/B"] as const;
const SORT_OPTIONS = ["By Time", "By Edge", "By Confidence"] as const;

export type League = (typeof LEAGUES)[number];
export type DateOption = (typeof DATE_OPTIONS)[number];
export type EdgeFilter = (typeof EDGE_FILTERS)[number];
export type SortOption = (typeof SORT_OPTIONS)[number];

interface SlateStats {
  totalGames: number;
  gamesWithEdge: number;
  tierACount: number;
}

interface Props {
  league: League;
  dateOption: DateOption;
  customDate: string | null;
  edgeFilter: EdgeFilter;
  sortBy: SortOption;
  stats: SlateStats | null;
  onLeagueChange: (league: League) => void;
  onDateChange: (option: DateOption) => void;
  onCustomDateChange: (date: string) => void;
  onEdgeFilterChange: (filter: EdgeFilter) => void;
  onSortChange: (sort: SortOption) => void;
}

export function FilterSidebar({
  league,
  dateOption,
  customDate,
  edgeFilter,
  sortBy,
  stats,
  onLeagueChange,
  onDateChange,
  onCustomDateChange,
  onEdgeFilterChange,
  onSortChange,
}: Props) {
  return (
    <aside className="w-60 bg-gray-900/60 border-r border-gray-800 p-4 space-y-5 overflow-y-auto shrink-0">
      {/* League */}
      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          League
        </h3>
        <div className="flex flex-col gap-1">
          {LEAGUES.map((l) => (
            <button
              key={l}
              onClick={() => onLeagueChange(l)}
              className={`text-left px-3 py-1.5 text-sm rounded-lg transition-colors ${
                league === l
                  ? "bg-green-600/20 text-green-400 border border-green-600/40"
                  : "text-gray-500 hover:text-gray-300 border border-transparent"
              }`}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* Date */}
      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Date
        </h3>
        <div className="flex gap-1 mb-2">
          {DATE_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => onDateChange(d)}
              className={`flex-1 px-2 py-1 text-xs rounded-md transition-colors ${
                dateOption === d && !customDate
                  ? "bg-green-600/20 text-green-400 border border-green-600/40"
                  : "text-gray-500 hover:text-gray-300 border border-gray-700/50"
              }`}
            >
              {d}
            </button>
          ))}
        </div>
        <input
          type="date"
          value={customDate ?? ""}
          onChange={(e) => onCustomDateChange(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-md px-2 py-1 text-xs text-gray-300 focus:border-green-600 focus:outline-none"
        />
      </div>

      {/* Edge filter */}
      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Filter
        </h3>
        <div className="flex flex-col gap-1">
          {EDGE_FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => onEdgeFilterChange(f)}
              className={`text-left px-3 py-1.5 text-xs rounded-md transition-colors ${
                edgeFilter === f
                  ? "bg-green-600/20 text-green-400 border border-green-600/40"
                  : "text-gray-500 hover:text-gray-300 border border-transparent"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Sort */}
      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Sort
        </h3>
        <div className="flex flex-col gap-1">
          {SORT_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => onSortChange(s)}
              className={`text-left px-3 py-1.5 text-xs rounded-md transition-colors ${
                sortBy === s
                  ? "bg-green-600/20 text-green-400 border border-green-600/40"
                  : "text-gray-500 hover:text-gray-300 border border-transparent"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Slate stats */}
      {stats && (
        <div className="bg-gray-800/40 rounded-xl p-3 text-xs text-gray-400">
          <span className="text-white font-medium">{stats.totalGames}</span> games
          {" · "}
          <span className="text-green-400 font-medium">{stats.gamesWithEdge}</span> edges
          {" · "}
          <span className="text-green-400 font-medium">{stats.tierACount}</span> Tier A
        </div>
      )}
    </aside>
  );
}
