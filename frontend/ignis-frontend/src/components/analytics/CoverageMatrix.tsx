import Link from "next/link";
import type { CoverageResponse } from "@/lib/types";

/**
 * Coverage matrix: rows = topics, columns = fuel/material class (or any dimension the API returns).
 * Darker cell = more records. Zero is shown in words, and links to Explore for non-empty cells.
 */
export function CoverageMatrix({ data }: { data: CoverageResponse }) {
  const maxCount = Math.max(1, ...data.cells.map((c) => c.count));
  const cellFor = (row: string, column: string) => data.cells.find((c) => c.row === row && c.column === column);

  return (
    <div className="panel overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <caption className="p-4 text-left">
          <span className="block font-medium">
            Records found in indexed PSI subset: {data.row_dimension} by {data.column_dimension}
          </span>
          <span className="block text-xs font-normal text-space-400">
            Each number is a count of investigations. &quot;No matching indexed record&quot; marks an empty combination.
          </span>
        </caption>
        <thead>
          <tr>
            <th scope="col" className="p-3 text-left font-medium text-space-300">{data.row_dimension}</th>
            {data.columns.map((c) => (
              <th key={c} scope="col" className="p-3 text-center font-medium text-space-300">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr key={row} className="border-t border-space-700/60">
              <th scope="row" className="p-3 text-left font-normal">{row}</th>
              {data.columns.map((column) => {
                const cell = cellFor(row, column);
                const count = cell?.count ?? 0;
                return (
                  <td key={column} className="p-1.5 text-center">
                    {count === 0 ? (
                      <div className="rounded-md border border-dashed border-space-600 px-2 py-3 text-xs text-space-400">
                        No matching indexed record
                      </div>
                    ) : (
                      <Link
                        href={`/explore?topic=${encodeURIComponent(row)}&material=${encodeURIComponent(column)}`}
                        className="block rounded-md px-2 py-3 font-medium text-space-950 hover:ring-2 hover:ring-flame-300"
                        style={{ backgroundColor: `rgba(107, 184, 245, ${0.35 + 0.65 * (count / maxCount)})` }}
                        aria-label={`${count} records for ${row} with ${column}. Open in Explore.`}
                      >
                        {count}
                      </Link>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
