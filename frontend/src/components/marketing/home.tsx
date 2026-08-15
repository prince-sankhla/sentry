import { Hero } from "./hero";
import { Navbar } from "./navbar";
import { SectionArchitecture } from "./section-architecture";
import { SectionComparison } from "./section-comparison";
import { SectionCta } from "./section-cta";
import { SectionEvidencePreservation } from "./section-evidence-preservation";
import { SectionPipeline } from "./section-pipeline";
import { SectionPreview } from "./section-preview";
import { SectionProblem } from "./section-problem";
import { SectionSources } from "./section-sources";
import { SectionWhy } from "./section-why";

/**
 * The SENTRY marketing homepage.
 *
 * Flow (per brand brief):
 * Hero → Problem → Why SENTRY → How Investigation Works →
 * Investigation Replay → Evidence Preservation →
 * Product Showcase → Trusted Sources → Architecture → CTA
 */
export function MarketingHome() {
  return (
    <div className="mkt min-h-screen">
      <Navbar />
      <main>
        <Hero />
        <SectionProblem />
        <SectionWhy />
        <SectionPipeline />
        <SectionComparison />
        <SectionEvidencePreservation />
        <SectionPreview />
        <SectionSources />
        <SectionArchitecture />
        <SectionCta />
      </main>
    </div>
  );
}
