import { notFound } from "next/navigation";
import { MarketingHome } from "@/components/marketing/home";
import AwardsPage from "@/app/awards/page";
import BuyersPage from "@/app/buyers/page";
import CasesPage from "@/app/cases/page";
import CompaniesPage from "@/app/companies/page";
import CompanyDetailPage from "@/app/companies/[companyId]/page";
import ContextPage from "@/app/context/page";
import DemoPage from "@/app/demo/page";
import GraphPage from "@/app/graph/page";
import InvestigatePage from "@/app/investigate/page";
import InvestigationsPage from "@/app/investigations/page";
import MapPage from "@/app/map/page";
import MonitoringPage from "@/app/monitoring/page";
import ProfilePage from "@/app/profile/page";
import RedFlagsPage from "@/app/red-flags/page";
import ReportsPage from "@/app/reports/page";
import ResearchPage from "@/app/research/page";
import ReviewPage from "@/app/review/page";
import ReviewInboxPage from "@/app/review/inbox/page";
import RiskPage from "@/app/risk/page";
import SettingsPage from "@/app/settings/page";
import TendersPage from "@/app/tenders/page";
import TenderDetailPage from "@/app/tenders/[tenderId]/page";
import TimelinePage from "@/app/timeline/page";
import VerificationPage from "@/app/verification/page";

export const dynamic = "force-dynamic";

// The production Vercel project is rooted at the repository level, while the
// application pages live under /frontend/src/app. This catch-all is therefore
// the production route boundary and must delegate every application pathname.
export default async function RootRoute({
  params,
  searchParams
}: {
  params: Promise<{ slug?: string[] }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const parts = slug ?? [];
  const props = { searchParams };

  if (parts.length === 0) return <MarketingHome />;

  switch (parts[0]) {
    case "awards":
      return <AwardsPage {...(props as any)} />;
    case "buyers":
      return <BuyersPage {...(props as any)} />;
    case "cases":
      return <CasesPage />;
    case "companies":
      if (parts.length === 2) {
        return (
          <CompanyDetailPage
            params={Promise.resolve({ companyId: parts[1] })}
            searchParams={searchParams}
          />
        );
      }
      return <CompaniesPage {...(props as any)} />;
    case "context":
      return <ContextPage {...(props as any)} />;
    case "demo":
      return <DemoPage />;
    case "graph":
      return <GraphPage {...(props as any)} />;
    case "investigate":
      return <InvestigatePage {...(props as any)} />;
    case "investigations":
      return <InvestigationsPage {...(props as any)} />;
    case "map":
      return <MapPage {...(props as any)} />;
    case "monitoring":
      return <MonitoringPage />;
    case "profile":
      return <ProfilePage {...(props as any)} />;
    case "red-flags":
      return <RedFlagsPage />;
    case "reports":
      return <ReportsPage {...(props as any)} />;
    case "research":
      return <ResearchPage {...(props as any)} />;
    case "review":
      if (parts[1] === "inbox") return <ReviewInboxPage />;
      return <ReviewPage {...(props as any)} />;
    case "risk":
      return <RiskPage {...(props as any)} />;
    case "settings":
      return <SettingsPage />;
    case "tenders":
      if (parts.length === 2) {
        return <TenderDetailPage params={Promise.resolve({ tenderId: parts[1] })} />;
      }
      return <TendersPage {...(props as any)} />;
    case "timeline":
      return <TimelinePage {...(props as any)} />;
    case "verification":
      return <VerificationPage {...(props as any)} />;
    default:
      notFound();
  }
}
