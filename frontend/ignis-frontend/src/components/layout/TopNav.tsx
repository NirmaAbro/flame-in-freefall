"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Flame, Menu, Search, Sparkles, X } from "lucide-react";
import { NAV_ITEMS } from "@/lib/constants";
import { USE_MOCK } from "@/lib/api";

/** Persistent top navigation: logo, 5 destinations, global search, data-source badge, Copilot shortcut. */
export function TopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState("");

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  function submitSearch(event: React.FormEvent) {
    event.preventDefault();
    const q = query.trim();
    router.push(q ? `/explore?q=${encodeURIComponent(q)}` : "/explore");
    setMenuOpen(false);
  }

  return (
    <header className="sticky top-0 z-40 border-b border-space-700 bg-space-950/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2 font-display text-lg">
          <Flame className="h-5 w-5 text-flame-500" aria-hidden />
          IGNIS
        </Link>

        {/* Desktop links */}
        <nav aria-label="Main" className="ml-4 hidden items-center gap-1 lg:flex">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive(item.href) ? "page" : undefined}
              className={`rounded-md px-3 py-1.5 text-sm ${
                isActive(item.href) ? "bg-space-700 text-space-100" : "text-space-300 hover:text-space-100"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <form onSubmit={submitSearch} role="search" className="relative hidden md:block">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-space-400" aria-hidden />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search investigations"
              placeholder="Search investigations"
              className="input w-64 pl-8"
            />
          </form>

          {USE_MOCK && (
            <span className="chip hidden border-flame-500/50 text-flame-300 sm:inline-flex" title="Showing built-in dummy data">
              Sample data
            </span>
          )}

          <Link href="/copilot" className="btn-primary hidden sm:inline-flex">
            <Sparkles className="h-4 w-4" aria-hidden />
            Ask Copilot
          </Link>

          <button
            className="btn-ghost lg:hidden"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="border-t border-space-700 px-4 py-3 lg:hidden">
          <form onSubmit={submitSearch} role="search" className="mb-3">
            <input value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search investigations" placeholder="Search investigations" className="input" />
          </form>
          <nav aria-label="Mobile" className="flex flex-col">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMenuOpen(false)}
                className={`rounded-md px-3 py-2 text-sm ${isActive(item.href) ? "bg-space-700" : "text-space-300"}`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}
