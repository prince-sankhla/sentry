/**
 * SENTRY mark — an emerald hexagonal evidence-core glyph. Pure SVG so it scales
 * crisply and needs no asset pipeline.
 *
 * Shared by the marketing navbar and the application shell: the mark in the
 * product header is the same mark the visitor clicked on the landing page.
 */
export function Logo({ className = "" }: { className?: string }) {
  return (
    <span
      className={`relative grid place-items-center overflow-hidden rounded-lg border border-accent/30 bg-accent/[0.08] text-accent ${className}`}
    >
      <svg width="60%" height="60%" viewBox="0 0 22 22" fill="none" aria-hidden="true">
        <path
          d="M11 1.5 19 6v10l-8 4.5L3 16V6l8-4.5Z"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        <path
          d="M11 6.5v9M6.5 9l9 4M15.5 9l-9 4"
          stroke="currentColor"
          strokeWidth="1.1"
          strokeOpacity="0.75"
        />
      </svg>
    </span>
  );
}

/**
 * Full lockup — mark plus wordmark and tagline. `tagline` is the small
 * uppercase line under SENTRY; pass `null` to suppress it in tight chrome.
 */
export function Wordmark({
  tagline = "Evidence over assumptions",
  size = "md"
}: {
  tagline?: string | null;
  size?: "sm" | "md";
}) {
  return (
    <>
      <Logo className={size === "sm" ? "h-8 w-8" : "h-9 w-9"} />
      <span className="hidden leading-none sm:block">
        <span
          className={`block font-semibold tracking-tight text-text ${
            size === "sm" ? "text-[15px]" : "text-base"
          }`}
        >
          SENTRY
        </span>
        {tagline && (
          <span className="mt-1 block text-[8px] font-semibold uppercase tracking-[0.22em] text-faint">
            {tagline}
          </span>
        )}
      </span>
    </>
  );
}
