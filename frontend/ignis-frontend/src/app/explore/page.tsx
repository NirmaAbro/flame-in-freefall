"use client";

/**
 * Explore: keyword search + filters + ranked results + pagination.
 * All state lives in the URL (?q=&topic=&page=...), so searches can be shared and
 * the back button works.
 */
import { Suspense, useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { FilterPanel } from "@/components/search/FilterPanel";
import { InvestigationCard } from "@/components/search/InvestigationCard";
import { Pagination } from "@/components/search/Pagination";
import { SearchBar } from "@/components/search/SearchBar";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/ui/States";
import { useAsync } from "@/hooks/useAsync";
import { aiSearch, getFilterOptions, listInvestigations } from "@/lib/api";
import type { InvestigationQuery } from "@/lib/types";

const PAGE_SIZE = 6;

function ExploreContent() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  // Read the current query from the URL.
  const query: InvestigationQuery = useMemo(
    () => ({
      q: params.get("q") ?? undefined,
      topic: params.get("topic") ?? undefined,
      platform: params.get("platform") ?? undefined,
      material: params.get("material") ?? undefined,
      measurement: params.get("measurement") ?? undefined,
      sort: params.get("sort") === "title" ? "title" : "relevance",
      page: Number(params.get("page") ?? 1),
      page_size: PAGE_SIZE,
    }),
    [params],
  );

  // Write changes back to the URL. Changing any filter resets to page 1.
  const updateUrl = useCallback(
    (changes: Record<string, string | undefined>, keepPage = false) => {
      const next = new URLSearchParams(params.toString());
      Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)));
      if (!keepPage) next.delete("page");
      router.replace(`${pathname}?${next.toString()}`);
    },
    [params, pathname, router],
  );

  const options = useAsync(getFilterOptions, []);
  const results = useAsync(() => listInvestigations(query), [params]);

  async function askInPlainLanguage(question: string) {
    const intent = await aiSearch(question);
    const q = intent.interpreted_as;
    router.replace(
      `${pathname}?${new URLSearchParams(
        Object.entries(q).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)]),
      ).toString()}`,
    );
  }

  return (
    <div className="page">
      <PageHeader
        title="Explore investigations"
        description="Search the indexed NASA records. Results are ranked deterministically: exact title or acronym first, then title, tags and summary."
      />

      <SearchBar
        initialValue={query.q ?? ""}
        onSearch={(q) => updateUrl({ q: q || undefined })}
        onAskInPlainLanguage={askInPlainLanguage}
      />

      <div className="mt-6 grid gap-6 lg:grid-cols-[260px_1fr]">
        {options.data ? (
          <FilterPanel
            options={options.data}
            values={query}
            onChange={(key, value) => updateUrl({ [key]: value || undefined })}
            onReset={() => router.replace(pathname)}
          />
        ) : (
          <LoadingBlock label="Loading filters..." />
        )}

        <section aria-live="polite">
          {results.loading && <LoadingBlock label="Searching..." />}
          {results.error && <ErrorBlock message={results.error} />}

          {results.data && (
            <>
              <div className="mb-3 flex items-center justify-between text-sm text-space-300">
                <p>{results.data.total} record{results.data.total === 1 ? "" : "s"} found in indexed subset</p>
                <label className="flex items-center gap-2">
                  Sort
                  <select
                    className="input w-auto py-1"
                    value={query.sort}
                    onChange={(e) => updateUrl({ sort: e.target.value })}
                  >
                    <option value="relevance">Relevance</option>
                    <option value="title">Title</option>
                  </select>
                </label>
              </div>

              {results.data.items.length === 0 ? (
                <EmptyBlock title="No matching indexed record" hint="Try fewer filters or different keywords. This only means nothing matched in the indexed subset." />
              ) : (
                <div className="space-y-4">
                  {results.data.items.map((item) => <InvestigationCard key={item.id} investigation={item} />)}
                </div>
              )}

              <Pagination
                page={results.data.page}
                pageSize={results.data.page_size}
                total={results.data.total}
                onPageChange={(page) => updateUrl({ page: String(page) }, true)}
              />
            </>
          )}
        </section>
      </div>
    </div>
  );
}

// useSearchParams requires a Suspense boundary in the Next.js App Router.
export default function ExplorePage() {
  return (
    <Suspense fallback={<LoadingBlock />}>
      <ExploreContent />
    </Suspense>
  );
}
