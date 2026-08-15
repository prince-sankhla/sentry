import type { Metadata } from "next";
import { MarketingHome } from "@/components/marketing/home";

export const metadata: Metadata = {
  title: "SENTRY — Evidence. Connected.",
  description:
    "Turn fragmented procurement records into one intelligent investigation workspace."
};

export default function HomePage() {
  return <MarketingHome />;
}
