"use client";

import Link from "next/link";
import { X } from "lucide-react";
import { useCompare } from "@/context/CompareContext";
import { MAX_COMPARE, MIN_COMPARE } from "@/lib/constants";

/**
 * Floating tray listing records selected for comparison.
 * The selected ids are shown until comparison metadata is loaded.
 */
export function CompareTray() {
  const { ids, remove, clear, isFull } = useCompare();
  if (ids.length === 0) return null;

  const label = (id: string) => id;

  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-space-600 bg-space-800/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <p className="text-sm text-space-300">
          Compare ({ids.length}/{MAX_COMPARE})
        </p>
        <ul className="flex flex-wrap gap-2">
          {ids.map((id) => (
            <li key={id} className="chip gap-1">
              {label(id)}
              <button onClick={() => remove(id)} aria-label={`Remove ${label(id)} from comparison`} className="rounded-full p-0.5 hover:bg-space-700">
                <X className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
        {isFull && <p className="text-xs text-flame-300">Maximum reached. Remove one to add another.</p>}
        <div className="ml-auto flex items-center gap-2">
          <button className="btn-ghost" onClick={clear}>Clear</button>
          {ids.length >= MIN_COMPARE ? (
            <Link href="/compare" className="btn-primary">Compare {ids.length} records</Link>
          ) : (
            <span className="text-xs text-space-400">Select at least {MIN_COMPARE} records</span>
          )}
        </div>
      </div>
    </div>
  );
}
