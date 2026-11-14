"use client";

/**
 * Compare: 2-4 selected records, deterministic table first, optional charts
 * (only for truly comparable values), and an optional AI explanation.
 */
import Link from "next/link";
import { useState } from "react";
import { Sparkles } from "lucide-react";
import { ChatPanel } from "@/components/copilot/ChatPanel";
import { ComparableChart } from "@/components/compare/ComparableChart";
import { ComparisonTable } from "@/components/compare/ComparisonTable";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/ui/States";
import { useCompare } from "@/context/CompareContext";
import { useAsync } from "@/hooks/useAsync";
import { compareInvestigations } from "@/lib/api";
import { MAX_COMPARE, MIN_COMPARE } from "@/lib/constants";

export default function ComparePage() {
  const { ids, clear } = useCompare();
  const [showAi, setShowAi] = useState(false);
  const enough = ids.length >= MIN_COMPARE;

  const result = useAsync(
    async () => (enough ? compareInvestigations(ids) : null),
    [ids.join(","), enough],
  );

  return (
    <div className="page space-y-8">
      <PageHeader
        title="Compare investigations"
        description={`Select ${MIN_COMPARE} to ${MAX_COMPARE} records in Explore. The table below never needs AI, and shows missing values as not reported.`}
        actions={ids.length > 0 && <button className="btn-secondary" onClick={clear}>Clear selection</button>}
      />

      {!enough && (
        <EmptyBlock
          title={`Select at least ${MIN_COMPARE} investigations`}
          hint="Use the Add to compare button on any result or detail page."
        />
      )}
      {!enough && <p className="text-center"><Link href="/explore" className="btn-primary">Go to Explore</Link></p>}

      {enough && result.loading && <LoadingBlock label="Aligning fields..." />}
      {enough && result.error && <ErrorBlock message={result.error} />}

      {result.data && (
        <>
          <ComparisonTable data={result.data} />

          <section aria-labelledby="charts">
            <h2 id="charts" className="mb-3 font-display text-2xl">Comparable values</h2>
            {result.data.comparable_parameters.length === 0 ? (
              <p className="panel p-4 text-sm text-space-300">
                No numeric parameter is reported with the same name and unit in two or more of these records,
                so no chart is drawn.
              </p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {result.data.comparable_parameters.map((p) => (
                  <ComparableChart key={`${p.name}-${p.unit}`} parameter={p} />
                ))}
              </div>
            )}
          </section>

          <ul className="list-disc space-y-1 pl-5 text-xs text-space-400">
            {result.data.notes.map((n) => <li key={n}>{n}</li>)}
          </ul>

          <section aria-labelledby="ai-explain">
            <h2 id="ai-explain" className="sr-only">AI explanation</h2>
            {!showAi ? (
              <button className="btn-secondary" onClick={() => setShowAi(true)}>
                <Sparkles className="h-4 w-4" aria-hidden /> Explain this comparison with AI
              </button>
            ) : (
              <div className="panel p-4">
                <p className="mb-4 text-sm text-space-300">Questions here only use the {ids.length} selected records.</p>
                <ChatPanel investigationIds={ids} />
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
