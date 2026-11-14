"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { SourceCitation } from "@/components/evidence/SourceCitation";
import { ReportedValue } from "@/components/ui/ReportedValue";
import { NOT_REPORTED } from "@/lib/constants";
import type { Investigation } from "@/lib/types";

const TABS = ["Overview", "Conditions & Methods", "Data & Files", "Publications", "Provenance"] as const;
type Tab = (typeof TABS)[number];

/** A label + value row. Missing values automatically show "Not reported". */
function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs text-space-400">{label}</dt>
      <dd className="mt-0.5 text-sm"><ReportedValue value={value} /></dd>
    </div>
  );
}

export function DetailTabs({ investigation: inv }: { investigation: Investigation }) {
  const [tab, setTab] = useState<Tab>("Overview");

  return (
    <div>
      <div role="tablist" aria-label="Investigation sections" className="flex flex-wrap gap-1 border-b border-space-700">
        {TABS.map((name) => (
          <button
            key={name}
            role="tab"
            id={`tab-${name}`}
            aria-selected={tab === name}
            aria-controls="tab-panel"
            onClick={() => setTab(name)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${
              tab === name ? "border-flame-500 text-space-100" : "border-transparent text-space-300 hover:text-space-100"
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      <div role="tabpanel" id="tab-panel" aria-labelledby={`tab-${tab}`} className="py-6">
        {tab === "Overview" && (
          <div className="space-y-6">
            <p className="max-w-3xl text-space-200"><ReportedValue value={inv.summary} /></p>
            <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Research area" value={inv.research_area} />
              <Field label="Project type" value={inv.project_type} />
              <Field label="Platform" value={inv.platform} />
              <Field label="Gravity environment" value={inv.environment} />
              <Field label="Fuel class" value={inv.fuel_classes.join(", ") || null} />
              <Field label="Topics" value={inv.topic_tags.join(", ") || null} />
            </dl>
          </div>
        )}

        {tab === "Conditions & Methods" && (
          <div className="space-y-6">
            <dl className="grid gap-4 sm:grid-cols-2">
              <Field label="Hardware" value={inv.hardware} />
              <Field label="Fuels / materials" value={inv.fuel_materials.join(", ") || null} />
              <Field label="Measurement types" value={inv.measurement_types.join(", ") || null} />
            </dl>
            <div>
              <h3 className="mb-2 font-medium">Reported conditions</h3>
              {inv.conditions.length === 0 ? (
                <p className="text-sm italic text-space-400">{NOT_REPORTED}</p>
              ) : (
                <ul className="space-y-3">
                  {inv.conditions.map((c) => (
                    <li key={c.name} className="panel p-3">
                      <p className="text-sm">
                        {c.name}: <strong>{c.value}</strong> {c.unit}
                      </p>
                      {c.context && <p className="text-xs text-space-300">{c.context}</p>}
                      <SourceCitation citation={c.citation} />
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        {tab === "Data & Files" &&
          (inv.files.length === 0 ? (
            <p className="text-sm italic text-space-400">{NOT_REPORTED}</p>
          ) : (
            <ul className="space-y-3">
              {inv.files.map((f) => (
                <li key={f.id} className="panel flex flex-wrap items-center justify-between gap-3 p-3">
                  <div>
                    <p className="text-sm">{f.title}</p>
                    <p className="text-xs text-space-400">
                      {f.file_type}. {f.reviewed ? "Reviewed by the team" : "Not yet reviewed"}
                    </p>
                    {f.description && <p className="text-xs text-space-300">{f.description}</p>}
                  </div>
                  <a href={f.source_url} target="_blank" rel="noreferrer" className="btn-secondary">
                    Open source <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                  </a>
                </li>
              ))}
            </ul>
          ))}

        {tab === "Publications" &&
          (inv.publications.length === 0 ? (
            <p className="text-sm italic text-space-400">{NOT_REPORTED}</p>
          ) : (
            <ul className="space-y-3">
              {inv.publications.map((p) => (
                <li key={p.id} className="panel p-3 text-sm">
                  <p>{p.title}</p>
                  <p className="text-xs text-space-400">{[p.authors, p.year].filter(Boolean).join(", ")}</p>
                  {p.doi && <p className="text-xs text-space-300">DOI: {p.doi}</p>}
                </li>
              ))}
            </ul>
          ))}

        {tab === "Provenance" && (
          <dl className="grid gap-4 sm:grid-cols-2">
            <Field label="Source identifier" value={inv.source_id} />
            <Field label="DOI" value={inv.doi} />
            <Field label="Source updated" value={inv.source_updated_at} />
            <Field label="Ingested into IGNIS" value={inv.ingested_at} />
            <Field label="Data status" value={inv.data_status === "sample" ? "Sample data (not verified)" : "Verified"} />
            <div>
              <dt className="text-xs text-space-400">Source page</dt>
              <dd className="mt-0.5 text-sm">
                <a href={inv.source_url} target="_blank" rel="noreferrer" className="text-diffuse-300 hover:underline">{inv.source_url}</a>
              </dd>
            </div>
          </dl>
        )}
      </div>
    </div>
  );
}
