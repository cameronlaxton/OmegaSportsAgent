"use client";

import { useState, type FormEvent } from "react";

interface Props {
  onSubmit: (query: string) => void;
  loading: boolean;
}

export function QueryInput({ onSubmit, loading }: Props) {
  const [query, setQuery] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (query.trim() && !loading) {
      onSubmit(query.trim());
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask a betting question... e.g. 'Lakers vs Warriors NBA -150/+130'"
        className="flex-1 bg-gray-800/80 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500/50"
        disabled={loading}
      />
      <button
        type="submit"
        disabled={loading || !query.trim()}
        className="px-6 py-3 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition-colors"
      >
        {loading ? "Analyzing..." : "Analyze"}
      </button>
    </form>
  );
}
