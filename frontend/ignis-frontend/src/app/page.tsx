"use client";

/**
 * Overview: hero + search, dataset snapshot, featured investigations,
 * research coverage chart, shortcuts. All numbers come from GET /dashboard/summary.
 */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FeaturedInvestigation } from "@/components/dashboard/FeaturedInvestigation";
import { HeroFlames } from "@/components/dashboard/HeroFlames";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { TopicChart } from "@/components/dashboard/TopicChart";
import { SearchBar } from "@/components/search/SearchBar";
import { ErrorBlock, LoadingBlock } from "@/components/ui/States";
import { useAsync } from "@/hooks/useAsync";
import { getDashboardSummary, listInvestigations } from "@/lib/api";
import { EXAMPLE_PROMPTS } from "@/lib/constants";

export default function OverviewPage() {
  const router = useRouter();
  const summary = useAsync(getDashboardSummary, []);
  const investigations = useAsync(async () => {
    const items = [];
    let page = 1;
    let total = 0;

    do {
      const result = await listInvestigations({ page, page_size: 100 });
      items.push(...result.items);
      total = result.total;
      page += 1;
    } while (items.length < total);

    return items;
  }, []);

  return (
    <div className="page space-y-14">
      {/* 1. Hero */}
      <section className="grid items-center gap-8 lg:grid-cols-2">
        <div className="space-y-5">
          <h1 className="font-display text-4xl leading-tight sm:text-5xl">
            Find, compare and question NASA&apos;s microgravity fire research
          </h1>
          <p className="max-w-xl text-space-300">
            IGNIS organises public NASA combustion investigations so you can see
            what was tested, how experiments differ, and what the indexed
            evidence does not yet cover.
          </p>
          <SearchBar
            large
            placeholder="Try: flame spread in microgravity"
            onSearch={(q) =>
              router.push(
                q ? `/explore?q=${encodeURIComponent(q)}` : "/explore",
              )
            }
          />
          <ul className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS.map((prompt) => (
              <li key={prompt}>
                <Link
                  href={`/copilot?prompt=${encodeURIComponent(prompt)}`}
                  className="chip hover:border-flame-400 hover:text-space-100"
                >
                  {prompt}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <HeroFlames />
      </section>

      {summary.loading && <LoadingBlock label="Loading dataset snapshot..." />}
      {summary.error && <ErrorBlock message={summary.error} />}

      {summary.data && (
        <>
          {/* 2. Dataset snapshot */}
          <section aria-labelledby="snapshot">
            <h2 id="snapshot" className="mb-4 font-display text-2xl">
              Dataset snapshot
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                label="Indexed investigations"
                value={summary.data.investigation_count}
              />
              <MetricCard
                label="Linked files"
                value={summary.data.file_count}
              />
              <MetricCard
                label="Publications"
                value={summary.data.publication_count}
              />
              <MetricCard
                label="Last ingestion"
                value={summary.data.last_ingestion_date}
              />
            </div>
            <p className="mt-3 text-xs text-space-400">
              {summary.data.dataset_note}
            </p>
          </section>

          {/* 3. All investigations */}
          <section aria-labelledby="investigations">
            <h2 id="investigations" className="mb-4 font-display text-2xl">
              All investigations
            </h2>
            {investigations.loading && <LoadingBlock />}
            {investigations.error && <ErrorBlock message={investigations.error} />}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {investigations.data?.map((inv) => (
                <FeaturedInvestigation key={inv.id} investigation={inv} />
              ))}
            </div>
          </section>

          {/* 4. Research coverage */}
          <section aria-labelledby="coverage">
            <h2 id="coverage" className="mb-4 font-display text-2xl">
              Research coverage
            </h2>
            <TopicChart data={summary.data.counts_by_topic} />
          </section>
        </>
      )}

      {/* 5. Start exploring */}
      <section aria-labelledby="start" className="grid gap-4 sm:grid-cols-3">
        <h2 id="start" className="sr-only">
          Start exploring
        </h2>
        {[
          {
            href: "/explore",
            title: "Explore investigations",
            text: "Search and filter records, then open the source.",
          },
          {
            href: "/compare",
            title: "Compare side by side",
            text: "Pick 2 to 4 records and see what differs.",
          },
          {
            href: "/research-map",
            title: "Open the research map",
            text: "See which topics are well covered and which are sparse.",
          },
        ].map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="panel p-5 hover:border-flame-400"
          >
            <p className="font-display text-xl">{card.title}</p>
            <p className="mt-1 text-sm text-space-300">{card.text}</p>
          </Link>
        ))}
      </section>
    </div>
  );
}
