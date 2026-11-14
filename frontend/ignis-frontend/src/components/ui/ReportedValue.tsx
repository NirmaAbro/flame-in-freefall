import { NOT_REPORTED } from "@/lib/constants";

/**
 * Renders a value from the API, or the standard "not reported" text when it is
 * null / empty. Use this everywhere so missing data never looks like zero.
 */
export function ReportedValue({ value }: { value: string | number | null | undefined }) {
  if (value === null || value === undefined || value === "") {
    return <span className="italic text-space-400">{NOT_REPORTED}</span>;
  }
  return <span>{value}</span>;
}
