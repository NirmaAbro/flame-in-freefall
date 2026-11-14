/**
 * The visual idea of the whole product: on Earth buoyancy pulls a flame into a
 * teardrop; in free fall there is no buoyancy and it becomes a sphere.
 * Pure SVG + CSS, no images. The sphere "breathes" slowly (disabled for reduced motion).
 */
export function HeroFlames() {
  return (
    <figure className="grid grid-cols-2 gap-4" aria-label="Comparison of a flame on Earth and a flame in microgravity">
      <div className="panel flex flex-col items-center gap-3 p-4">
        <svg viewBox="0 0 120 150" className="h-40 w-32" role="img" aria-label="Teardrop flame">
          <defs>
            <radialGradient id="earthFlame" cx="50%" cy="75%" r="60%">
              <stop offset="0%" stopColor="#ffe3a8" />
              <stop offset="55%" stopColor="#ff9650" />
              <stop offset="100%" stopColor="#d95f14" stopOpacity="0.1" />
            </radialGradient>
          </defs>
          <path d="M60 10 C 78 50, 100 70, 90 105 C 84 130, 36 130, 30 105 C 20 70, 46 52, 60 10 Z" fill="url(#earthFlame)" />
          <rect x="54" y="128" width="12" height="18" rx="2" fill="#26375a" />
        </svg>
        <figcaption className="text-center text-sm">
          <span className="font-medium">On Earth</span>
          <span className="block text-space-300">Rising hot gas stretches the flame upward.</span>
        </figcaption>
      </div>

      <div className="panel flex flex-col items-center gap-3 p-4">
        <svg viewBox="0 0 120 150" className="h-40 w-32" role="img" aria-label="Spherical flame">
          <defs>
            <radialGradient id="spaceFlame" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#d9efff" stopOpacity="0.9" />
              <stop offset="45%" stopColor="#6bb8f5" stopOpacity="0.85" />
              <stop offset="100%" stopColor="#3d96e0" stopOpacity="0" />
            </radialGradient>
          </defs>
          <g className="animate-breathe" style={{ transformOrigin: "60px 75px" }}>
            <circle cx="60" cy="75" r="52" fill="url(#spaceFlame)" />
          </g>
        </svg>
        <figcaption className="text-center text-sm">
          <span className="font-medium">In free fall</span>
          <span className="block text-space-300">No buoyancy. Oxygen arrives by diffusion.</span>
        </figcaption>
      </div>
    </figure>
  );
}
