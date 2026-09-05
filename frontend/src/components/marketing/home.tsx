import { Hero } from "./hero";
import { Navbar } from "./navbar";
import { SectionArchitecture } from "./section-architecture";
import { SectionCapabilities } from "./section-capabilities";
import { SectionComparison } from "./section-comparison";
import { SectionCta } from "./section-cta";
import { SectionEvidencePreservation } from "./section-evidence-preservation";
import { SectionPipeline } from "./section-pipeline";
import { SectionPreview } from "./section-preview";
import { SectionProblem } from "./section-problem";
import { SectionSources } from "./section-sources";
import { SectionWhy } from "./section-why";

/**
 * Marketing homepage: brand statement → problem → connected investigation →
 * platform surface → workflow → evidence → product → architecture → CTA.
 */
export function MarketingHome() {
  return (
    <div className="mkt min-h-screen">
      <Navbar />
      <main>
        <Hero />
        <SectionProblem />
        <SectionWhy />
        <SectionCapabilities />
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
