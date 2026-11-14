import Link from "next/link";
import { ReportedValue } from "@/components/ui/ReportedValue";
import type { CompareResponse } from "@/lib/types";

/**
 * Deterministic field-by-field table. Works without AI.
 * Rows where records differ are marked, so differences stand out.
 */
export function ComparisonTable({ data }: { data: CompareResponse }) {
  return (
    <div className="panel overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-left text-sm">
        <caption className="sr-only">Field-by-field comparison of selected investigations</caption>
        <thead>
          <tr className="border-b border-space-700">
            <th scope="col" className="w-44 p-3 font-medium text-space-300">Field</th>
            {data.investigations.map((inv) => (
              <th key={inv.id} scope="col" className="p-3 align-top">
                <Link href={`/investigations/${inv.id}`} className="font-display text-lg hover:text-flame-300">
                  {inv.acronym ?? inv.title}
                </Link>
                <p className="text-xs font-normal text-space-400">{inv.title}</p>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => {
            const values = data.investigations.map((inv) => row.cells[inv.id]?.value ?? null);
            const differs = new Set(values.map((v) => v ?? "__missing__")).size > 1;
            return (
              <tr key={row.field} className="border-b border-space-700/60 last:border-0">
                <th scope="row" className="p-3 align-top font-medium text-space-300">
                  {row.field}
                  {differs && <span className="mt-0.5 block text-xs font-normal text-flame-300">differs</span>}
                </th>
                {values.map((value, index) => (
                  <td key={data.investigations[index].id} className="p-3 align-top">
                    <ReportedValue value={value} />
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
