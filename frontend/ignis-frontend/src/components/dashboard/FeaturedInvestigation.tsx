import Link from "next/link";
import type { Investigation } from "@/lib/types";

/** Compact card for the "Featured investigations" row on Overview. */
export function FeaturedInvestigation({ investigation }: { investigation: Investigation }) {
  return (
    <article className="panel flex flex-col p-4">
      <p className="text-xs text-space-400">{investigation.research_area ?? "Research area not reported"}</p>
      <h3 className="mt-1 font-display text-xl">{investigation.acronym ?? investigation.title}</h3>
      <p className="text-sm text-space-300">{investigation.title}</p>
      <p className="mt-3 line-clamp-3 flex-1 text-sm text-space-200">{investigation.summary}</p>
      <div className="mt-4 flex items-center justify-between text-sm">
        <a href={investigation.source_url} target="_blank" rel="noreferrer" className="text-diffuse-300 hover:underline">
          NASA source
        </a>
        <Link href={`/investigations/${investigation.id}`} className="btn-secondary">
          Open details
        </Link>
      </div>
    </article>
  );
}
