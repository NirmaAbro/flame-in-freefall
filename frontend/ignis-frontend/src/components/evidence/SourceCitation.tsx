import { ExternalLink } from "lucide-react";
import type { SourceCitation as Citation } from "@/lib/types";

/** Small provenance line shown directly under the value it supports. */
export function SourceCitation({ citation }: { citation: Citation }) {
  return (
    <p className="mt-1 text-xs text-space-400">
      Source:{" "}
      <a href={citation.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-diffuse-300 hover:underline">
        {citation.source_name}
        <ExternalLink className="h-3 w-3" aria-hidden />
      </a>
      {citation.location && <> ({citation.location})</>}. Accessed {citation.accessed_at}.
    </p>
  );
}
