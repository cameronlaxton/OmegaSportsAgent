"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { healthCheck } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/", label: "Slate" },
  { href: "/diagnostics", label: "Diagnostics" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    healthCheck()
      .then((r) => setHealthy(r.status === "ok"))
      .catch(() => setHealthy(false));
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Topbar */}
      <header className="h-12 bg-gray-900 border-b border-gray-800 flex items-center px-4 shrink-0">
        <Link href="/" className="text-lg font-bold tracking-tight mr-8">
          <span className="text-green-400">Omega</span>
          <span className="text-white">SportsAgent</span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  active
                    ? "text-green-400 bg-green-600/10"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <span
            className={`w-2 h-2 rounded-full ${
              healthy === null
                ? "bg-gray-600"
                : healthy
                  ? "bg-green-400"
                  : "bg-red-400"
            }`}
            title={
              healthy === null
                ? "Checking..."
                : healthy
                  ? "Backend healthy"
                  : "Backend unreachable"
            }
          />
        </div>
      </header>

      {/* Page content */}
      <div className="flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
