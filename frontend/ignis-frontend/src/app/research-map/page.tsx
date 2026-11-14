"use client";

/** Research Map: coverage matrix, topic chart and the methodology behind the word "gap". */
import { CoverageMatrix } from "@/components/analytics/CoverageMatrix";
import { TopicChart } from "@/components/dashboard/TopicChart";
import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorBlock, LoadingBlock } from "@/components/ui/States";
import { useAsync } from "@/hooks/useAsync";
import { getCoverage, getDashboardSummary } from "@/lib/api";

export default function ResearchMapPage() {
  const coverage = useAsync(getCoverage, []);
  const summary = useAsync(getDashboardSummary, []);

  return (
    <div className="page space-y-8">
      <PageHeader
        title="Research map"
        description="See which topic and fuel combinations are well represented in the indexed records, and which are sparse. Sparse means sparse in this dataset, not absent from science."
      />

      {coverage.loading && <LoadingBlock label="Calculating coverage..." />}
      {coverage.error && <ErrorBlock message={coverage.error} />}

      {coverage.data && (
        <>
          <CoverageMatrix data={coverage.data} />
          {summary.data && <TopicChart data={summary.data.counts_by_topic} />}

          <section className="panel p-5" aria-labelledby="method">
            <h2 id="method" className="font-display text-xl">How to read this map</h2>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-space-300">
              {coverage.data.method_notes.map((note) => <li key={note}>{note}</li>)}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
