"use client";

import Link from "next/link";
import { ExternalLink, GitCompareArrows } from "lucide-react";
import { useCompare } from "@/context/CompareContext";
import type { InvestigationListItem } from "@/lib/types";

/** One Explore result: title, summary, tags, why it matched, source link, Add to Compare. */
export function InvestigationCard({ investigation }: { investigation: InvestigationListItem }) {
  const { isSelected, toggle, isFull } = useCompare();
  const selected = isSelected(investigation.id);

  return (
    <article className="panel p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-xl">
            <Link href={`/investigations/${investigation.id}`} className="hover:text-flame-300">
              {investigation.acronym ? `${investigation.acronym}: ` : ""}
              {investigation.title}
            </Link>
          </h3>
          <p className="text-xs text-space-400">{investigation.research_area ?? "Research area not reported"}</p>
        </div>
        <button
          onClick={() => toggle(investigation.id)}
          disabled={!selected && isFull}
          aria-pressed={selected}
          className={selected ? "btn-primary" : "btn-secondary"}
        >
          <GitCompareArrows className="h-4 w-4" aria-hidden />
          {selected ? "Added to compare" : "Add to compare"}
        </button>
      </div>

      <p className="mt-3 max-w-3xl text-sm text-space-200">
        {investigation.summary ?? <span className="italic text-space-400">No summary in indexed record</span>}
      </p>

      {investigation.topic_tags.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2" aria-label="Topics">
          {investigation.topic_tags.map((tag) => (
            <li key={tag} className="chip">{tag}</li>
          ))}
        </ul>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-space-400">
        {investigation.match_reasons.length > 0 && <span>Matched on: {investigation.match_reasons.join(", ")}</span>}
        <a href={investigation.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-diffuse-300 hover:underline">
          NASA PSI source <ExternalLink className="h-3 w-3" aria-hidden />
        </a>
      </div>
    </article>
  );
}
