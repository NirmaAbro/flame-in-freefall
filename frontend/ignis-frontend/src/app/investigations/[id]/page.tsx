"use client";

/** Investigation detail: header, compare action, and 5 tabs (see DetailTabs). */
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, ExternalLink, GitCompareArrows } from "lucide-react";
import { DetailTabs } from "@/components/investigation/DetailTabs";
import { ErrorBlock, LoadingBlock } from "@/components/ui/States";
import { useCompare } from "@/context/CompareContext";
import { useAsync } from "@/hooks/useAsync";
import { getInvestigation } from "@/lib/api";

export default function InvestigationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, loading, error } = useAsync(() => getInvestigation(id), [id]);
  const { isSelected, toggle, isFull } = useCompare();

  return (
    <div className="page">
      <Link href="/explore" className="mb-4 inline-flex items-center gap-1 text-sm text-space-300 hover:text-space-100">
        <ArrowLeft className="h-4 w-4" aria-hidden /> Back to Explore
      </Link>

      {loading && <LoadingBlock />}
      {error && <ErrorBlock message={error} />}

      {data && (
        <>
          <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
            <div>
              {data.data_status === "sample" && (
                <p className="chip mb-2 border-flame-500/50 text-flame-300">Sample data, not verified against PSI</p>
              )}
              <h1 className="font-display text-3xl">{data.acronym ? `${data.acronym}: ` : ""}{data.title}</h1>
              <a href={data.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-sm text-diffuse-300 hover:underline">
                Open NASA PSI source <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              </a>
            </div>
            <button
              className={isSelected(data.id) ? "btn-primary" : "btn-secondary"}
              onClick={() => toggle(data.id)}
              disabled={!isSelected(data.id) && isFull}
              aria-pressed={isSelected(data.id)}
            >
              <GitCompareArrows className="h-4 w-4" aria-hidden />
              {isSelected(data.id) ? "Added to compare" : "Add to compare"}
            </button>
          </header>
          <DetailTabs investigation={data} />
        </>
      )}
    </div>
  );
}
