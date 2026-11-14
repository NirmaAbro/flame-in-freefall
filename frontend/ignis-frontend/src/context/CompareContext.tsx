"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { MAX_COMPARE } from "@/lib/constants";

interface CompareContextValue {
  ids: string[];
  isSelected: (id: string) => boolean;
  isFull: boolean;
  toggle: (id: string) => void;
  remove: (id: string) => void;
  clear: () => void;
}

const CompareContext = createContext<CompareContextValue | null>(null);
const STORAGE_KEY = "ignis-compare-ids";

/** Holds the records selected for comparison; shared by Explore, detail page, tray and Compare page. */
export function CompareProvider({ children }: { children: React.ReactNode }) {
  const [ids, setIds] = useState<string[]>([]);

  // Restore after first render (not during, to avoid server/client mismatch).
  useEffect(() => {
    try {
      const saved = window.sessionStorage.getItem(STORAGE_KEY);
      if (saved) setIds(JSON.parse(saved));
    } catch {
      /* storage unavailable: start empty */
    }
  }, []);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
    } catch {
      /* ignore */
    }
  }, [ids]);

  const toggle = useCallback((id: string) => {
    setIds((current) => {
      if (current.includes(id)) return current.filter((x) => x !== id);
      if (current.length >= MAX_COMPARE) return current; // tray shows the limit message
      return [...current, id];
    });
  }, []);

  const value = useMemo<CompareContextValue>(
    () => ({
      ids,
      isSelected: (id) => ids.includes(id),
      isFull: ids.length >= MAX_COMPARE,
      toggle,
      remove: (id) => setIds((current) => current.filter((x) => x !== id)),
      clear: () => setIds([]),
    }),
    [ids, toggle],
  );

  return <CompareContext.Provider value={value}>{children}</CompareContext.Provider>;
}

export function useCompare(): CompareContextValue {
  const context = useContext(CompareContext);
  if (!context) throw new Error("useCompare must be used inside <CompareProvider>");
  return context;
}
