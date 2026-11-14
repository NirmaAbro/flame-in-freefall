import { AlertTriangle, Loader2, SearchX } from "lucide-react";

/** Shown while an API call is running. */
export function LoadingBlock({ label = "Loading..." }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 p-6 text-sm text-space-300">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      {label}
    </div>
  );
}

/** Shown when an API call fails. Always says what to do next. */
export function ErrorBlock({ message }: { message: string }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div>
        <p className="font-medium">Could not load this data.</p>
        <p className="mt-1 text-red-200/80">{message}</p>
      </div>
    </div>
  );
}

/** Shown when a call succeeds but returns nothing. */
export function EmptyBlock({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-space-600 p-10 text-center">
      <SearchX className="h-6 w-6 text-space-400" aria-hidden />
      <p className="font-medium">{title}</p>
      {hint && <p className="max-w-md text-sm text-space-300">{hint}</p>}
    </div>
  );
}
