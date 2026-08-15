import { InvestigationWorkspace } from "../investigation-workspace";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<{
    q?: string;
  }>;
};

export default async function InvestigatePage({ searchParams }: PageProps) {
  const params = await searchParams;
  return <InvestigationWorkspace initialQuery={(params.q ?? "").trim()} />;
}
