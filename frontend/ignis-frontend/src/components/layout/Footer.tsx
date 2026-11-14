import { CHALLENGE_URL, PSI_REPO_URL } from "@/lib/constants";

/** Global data-provenance footer. Per-value provenance is still shown next to values. */
export function Footer() {
  return (
    <footer className="mt-16 border-t border-space-700 bg-space-900">
      <div className="page space-y-2 py-8 text-sm text-space-300">
        <p>
          Records are derived from the{" "}
          <a className="text-diffuse-300 hover:underline" href={PSI_REPO_URL} target="_blank" rel="noreferrer">
            NASA Physical Sciences Informatics (PSI) repository
          </a>
          . Always verify against the original NASA page.
        </p>
        <p>
          IGNIS is a research discovery prototype for the{" "}
          <a className="text-diffuse-300 hover:underline" href={CHALLENGE_URL} target="_blank" rel="noreferrer">
            NASA Space Apps 2026 &quot;Flame in Freefall&quot; challenge
          </a>
          . It is not a fire-prediction system, not a flight-certified safety tool, and not a replacement for NASA engineering review.
        </p>
      </div>
    </footer>
  );
}
