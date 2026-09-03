import { notFound } from "next/navigation";
import { MarketingHome } from "@/components/marketing/home";
import AwardsPage from "@/app/awards/page";
import CompaniesPage from "@/app/companies/page";
import CompanyDetailPage from "@/app/companies/[companyId]/page";
import GraphPage from "@/app/graph/page";
import InvestigatePage from "@/app/investigate/page";
import InvestigationsPage from "@/app/investigations/page";
import MapPage from "@/app/map/page";
import ProfilePage from "@/app/profile/page";
import ReportsPage from "@/app/reports/page";
import RiskPage from "@/app/risk/page";
import SettingsPage from "@/app/settings/page";
import TendersPage from "@/app/tenders/page";
import TenderDetailPage from "@/app/tenders/[tenderId]/page";
import TimelinePage from "@/app/timeline/page";

export const dynamic = "force-dynamic";

// Vercel previously built the real Next app from /frontend but the project was
// configured at repository root, so the generated .next output was not served.
// This root route intentionally delegates every public application route to the
// existing frontend page modules without duplicating business/UI code.
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
    case "graph":
      return <GraphPage {...(props as any)} />;
    case "investigate":
      return <InvestigatePage {...(props as any)} />;
    case "investigations":
      return <InvestigationsPage {...(props as any)} />;
    case "map":
      return <MapPage {...(props as any)} />;
    case "profile":
      return <ProfilePage {...(props as any)} />;
    case "reports":
      return <ReportsPage {...(props as any)} />;
    case "risk":
      return <RiskPage {...(props as any)} />;
    case "settings":
      return <SettingsPage {...(props as any)} />;
    case "tenders":
      if (parts.length === 2) {
        return <TenderDetailPage params={Promise.resolve({ tenderId: parts[1] })} />;
      }
      return <TendersPage {...(props as any)} />;
    case "timeline":
      return <TimelinePage {...(props as any)} />;
    default:
      notFound();
  }
}
