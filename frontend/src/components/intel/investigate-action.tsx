import { Search } from "lucide-react";

import { Button, type ButtonSize, type ButtonVariant } from "@/components/ui/button";

/** Consistent one-click investigation affordance used across every procurement record surface. */
export function InvestigateAction({
  query,
  label = "Investigate",
  size = "sm",
  variant = "secondary"
}: {
  query: string;
  label?: string;
  size?: ButtonSize;
  variant?: ButtonVariant;
}) {
  const clean = query.trim();
  if (!clean) return null;

  return (
    <Button
      href={`/investigate?q=${encodeURIComponent(clean)}`}
      size={size}
      variant={variant}
      icon={<Search className="h-3.5 w-3.5" aria-hidden="true" />}
      title={`Investigate ${clean}`}
    >
      {label}
    </Button>
  );
}
