import type { FilterOptions, InvestigationQuery } from "@/lib/types";

type FilterKey = "topic" | "platform" | "material" | "measurement";

const FILTERS: { key: FilterKey; label: string; optionsKey: keyof FilterOptions }[] = [
  { key: "topic", label: "Research topic", optionsKey: "topics" },
  { key: "material", label: "Fuel / material class", optionsKey: "materials" },
  { key: "platform", label: "Platform", optionsKey: "platforms" },
  { key: "measurement", label: "Measurement type", optionsKey: "measurements" },
];

interface FilterPanelProps {
  options: FilterOptions;
  values: InvestigationQuery;
  onChange: (key: FilterKey, value: string) => void;
  onReset: () => void;
}

/**
 * Only values that exist in the data are offered (the backend decides the options),
 * so a filter never leads to a guaranteed-empty result.
 */
export function FilterPanel({ options, values, onChange, onReset }: FilterPanelProps) {
  return (
    <aside aria-label="Filters" className="panel space-y-4 p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-medium">Filters</h2>
        <button className="text-xs text-diffuse-300 hover:underline" onClick={onReset}>Reset</button>
      </div>
      {FILTERS.map(({ key, label, optionsKey }) => (
        <div key={key}>
          <label htmlFor={`filter-${key}`} className="mb-1 block text-sm text-space-300">{label}</label>
          <select
            id={`filter-${key}`}
            className="input"
            value={values[key] ?? ""}
            onChange={(e) => onChange(key, e.target.value)}
          >
            <option value="">Any</option>
            {options[optionsKey].map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </div>
      ))}
    </aside>
  );
}
