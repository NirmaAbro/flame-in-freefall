/** One number from the dataset snapshot. Values must come from the dashboard API. */
export function MetricCard({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return (
    <div className="panel p-4">
      <p className="text-sm text-space-300">{label}</p>
      <p className="mt-1 font-display text-3xl">{value}</p>
      {note && <p className="mt-1 text-xs text-space-400">{note}</p>}
    </div>
  );
}
