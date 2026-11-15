"use client";

/**
 * Habitat ranking: pick a habitat, see investigations ordered by the backend,
 * and read the formula the backend sends. Score null = no tests (never shown as 0).
 */
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/ui/States";
import { useAsync } from "@/hooks/useAsync";
import { exportTestsCsv, getHabitats, rankInvestigations } from "@/lib/api";
import { toHabitatOptions, toRankView, type RankedRow } from "@/lib/habitatView";

function ScoreCell({ row }: { row: RankedRow }) {
  if (row.score === null) {
    return <span className="chip border-space-600 text-space-400">No tests</span>;
  }
  return (
    <div className="text-right">
      <p className="font-display text-2xl">{row.score.toFixed(3)}</p>
      {row.testsMatched !== null && row.testsTotal !== null && (
        <p className="text-xs text-space-400">{row.testsMatched} of {row.testsTotal} tests</p>
      )}
    </div>
  );
}

export default function HabitatRankingPage() {
  const [habitatId, setHabitatId] = useState<string | null>(null);
  const [csvError, setCsvError] = useState<string | null>(null);

  const habitatsState = useAsync(async () => toHabitatOptions(await getHabitats()), []);
  const habitats = habitatsState.data ?? [];

  // Select the first habitat once the list arrives.
  useEffect(() => {
    if (!habitatId && habitats.length > 0) setHabitatId(habitats[0].id);
  }, [habitats, habitatId]);

  const ranking = useAsync(
    async () => (habitatId ? toRankView(await rankInvestigations(habitatId)) : null),
    [habitatId],
  );

  const selected = habitats.find((h) => h.id === habitatId);
  // Keep the backend's order. Records without tests go in their own list.
  const scored = useMemo(() => ranking.data?.rows.filter((r) => r.score !== null) ?? [], [ranking.data]);
  const unscored = useMemo(() => ranking.data?.rows.filter((r) => r.score === null) ?? [], [ranking.data]);

  async function downloadCsv() {
    setCsvError(null);
    try {
      const blob = await exportTestsCsv();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "tests.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setCsvError(err instanceof Error ? err.message : "Could not download the CSV.");
    }
  }

  return (
    <div className="page space-y-8">
      <PageHeader
        title="Habitat ranking"
        description="Choose a habitat to see which investigations have tests closest to its conditions. The score comes from the backend, and the formula is shown below."
        actions={
          <button className="btn-secondary" onClick={downloadCsv}>
            <Download className="h-4 w-4" aria-hidden /> Download tests (CSV)
          </button>
        }
      />
      {csvError && <ErrorBlock message={csvError} />}

      {habitatsState.loading && <LoadingBlock label="Loading habitats..." />}
      {habitatsState.error && <ErrorBlock message={habitatsState.error} />}

      {habitats.length > 0 && (
        <div role="radiogroup" aria-label="Habitat" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {habitats.map((h) => (
            <button
              key={h.id}
              role="radio"
              aria-checked={h.id === habitatId}
              onClick={() => setHabitatId(h.id)}
              className={`panel p-4 text-left ${h.id === habitatId ? "border-flame-400" : "hover:border-space-400"}`}
            >
              <p className="font-display text-lg">{h.name}</p>
              {h.description && <p className="mt-1 text-sm text-space-300">{h.description}</p>}
            </button>
          ))}
        </div>
      )}

      {ranking.loading && <LoadingBlock label="Ranking investigations..." />}
      {ranking.error && <ErrorBlock message={ranking.error} />}

      {ranking.data && (
        <>
          <section aria-labelledby="formula" className="panel p-5">
            <h2 id="formula" className="font-display text-xl">How the score is calculated</h2>
            {ranking.data.formula ? (
              <p className="mt-2 whitespace-pre-wrap text-sm text-space-200">{ranking.data.formula}</p>
            ) : (
              <p className="mt-2 text-sm italic text-space-400">The backend did not send a formula text.</p>
            )}
          </section>

          <section aria-labelledby="ranked">
            <h2 id="ranked" className="mb-3 font-display text-2xl">
              Best fit for {selected?.name ?? "this habitat"}
            </h2>
            {ranking.data.rows.length === 0 ? (
              <EmptyBlock
                title="No ranking rows recognised"
                hint="The response arrived but no list was found. Check the field names in src/lib/habitatView.ts."
              />
            ) : (
              <ol className="space-y-3">
                {scored.map((row, index) => (
                  <li key={row.id} className="panel flex items-center gap-4 p-4">
                    <span className="w-8 text-center font-display text-2xl text-space-400">{index + 1}</span>
                    <div className="flex-1">
                      <Link href={`/investigations/${row.id}`} className="font-display text-xl hover:text-flame-300">
                        {row.label}
                      </Link>
                      {row.title && row.title !== row.label && <p className="text-sm text-space-300">{row.title}</p>}
                    </div>
                    <ScoreCell row={row} />
                  </li>
                ))}
              </ol>
            )}
          </section>

          {unscored.length > 0 && (
            <section aria-labelledby="notests">
              <h2 id="notests" className="mb-1 font-display text-xl">Not ranked: no tests</h2>
              <p className="mb-3 text-sm text-space-300">
                These investigations have no tests to score for this habitat. That is not a score of zero.
              </p>
              <ul className="space-y-2">
                {unscored.map((row) => (
                  <li key={row.id} className="panel flex items-center justify-between p-3">
                    <Link href={`/investigations/${row.id}`} className="hover:text-flame-300">{row.label}</Link>
                    <ScoreCell row={row} />
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}