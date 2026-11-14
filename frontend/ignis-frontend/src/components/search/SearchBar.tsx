"use client";

import { useEffect, useState } from "react";
import { Search, Sparkles } from "lucide-react";

interface SearchBarProps {
  initialValue?: string;
  placeholder?: string;
  /** Plain keyword search. */
  onSearch: (text: string) => void;
  /** "Ask in plain language": the backend turns the question into filters (POST /ai/search). */
  onAskInPlainLanguage?: (text: string) => void;
  large?: boolean;
}

export function SearchBar({ initialValue = "", placeholder, onSearch, onAskInPlainLanguage, large }: SearchBarProps) {
  const [text, setText] = useState(initialValue);

  // Keep the field in sync when the URL changes (back button, example prompts).
  useEffect(() => setText(initialValue), [initialValue]);

  return (
    <form
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        onSearch(text.trim());
      }}
      className="flex flex-col gap-2 sm:flex-row"
    >
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-space-400" aria-hidden />
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-label="Search investigations"
          placeholder={placeholder ?? "Search by title, acronym, topic or fuel"}
          className={`input pl-9 ${large ? "py-3 text-base" : ""}`}
        />
      </div>
      <button type="submit" className="btn-primary">Search</button>
      {onAskInPlainLanguage && (
        <button type="button" className="btn-secondary" onClick={() => onAskInPlainLanguage(text.trim())} disabled={!text.trim()}>
          <Sparkles className="h-4 w-4" aria-hidden />
          Ask in plain language
        </button>
      )}
    </form>
  );
}
