export const NOT_REPORTED = "Not reported in indexed record";

export const CHALLENGE_URL = "https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/";
export const PSI_REPO_URL = "https://psi.nasa.gov/physci/repo";

/** Max / min records in Compare, from the plan (2-4). */
export const MIN_COMPARE = 2;
export const MAX_COMPARE = 4;

export const EXAMPLE_PROMPTS = [
  "Find investigations related to flame spread",
  "Compare FLEX and BASS",
  "What evidence is available about oxygen concentration?",
  "Which topic areas have the fewest indexed records?",
];

export const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/explore", label: "Explore" },
  { href: "/compare", label: "Compare" },
  { href: "/research-map", label: "Research Map" },
  { href: "/copilot", label: "AI Copilot" },
] as const;
