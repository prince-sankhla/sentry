"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useTransition } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import type { CompanyTenderSort } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { SearchInput, Select } from "@/components/ui/input";

type Props = {
  limit: number;
  offset: number;
  query: string;
  sort: CompanyTenderSort;
  total: number;
};

const sortOptions: { label: string; value: CompanyTenderSort }[] = [
  { label: "Latest activity", value: "latest" },
  { label: "Publication date", value: "published_date" },
  { label: "Tender value", value: "value" },
  { label: "Award value", value: "award_value" },
  { label: "Title", value: "title" }
];

export function CompanyInvestigationControls({ limit, offset, query, sort, total }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));
  const hasPrevious = offset > 0;
  const hasNext = offset + limit < total;

  function updateParams(updates: Record<string, string | number | null>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value === "") {
        params.delete(key);
      } else {
        params.set(key, String(value));
      }
    }

    startTransition(() => {
      router.push(`${pathname}?${params.toString()}`);
    });
  }

  function onSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const nextQuery = String(formData.get("q") ?? "").trim();
    updateParams({ q: nextQuery || null, offset: 0 });
  }

  return (
    <div className="rounded-2xl border border-border bg-surface/70 p-5">
      <form className="grid gap-3 lg:grid-cols-[1fr_190px_auto]" onSubmit={onSearch}>
        <label className="relative block">
          <span className="sr-only">Search procurement history</span>
          <SearchInput
            defaultValue={query}
            name="q"
            placeholder="Search procurement history"
            type="search"
            pending={isPending}
          />
        </label>
        <Select
          onChange={(event) => updateParams({ sort: event.target.value, offset: 0 })}
          value={sort}
        >
          {sortOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
        <Button variant="primary" type="submit" disabled={isPending}>
          Search
        </Button>
      </form>

      <div className="mt-5 flex flex-col gap-3 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
        <div aria-live="polite">{isPending ? "Loading procurement history..." : `Page ${page} of ${pages}`}</div>
        <div className="flex gap-2">
          <Button
            variant="subtle"
            size="sm"
            disabled={!hasPrevious || isPending}
            onClick={() => updateParams({ offset: Math.max(0, offset - limit) })}
            icon={<ChevronLeft className="h-4 w-4" aria-hidden="true" />}
          >
            Previous
          </Button>
          <Button
            variant="subtle"
            size="sm"
            disabled={!hasNext || isPending}
            onClick={() => updateParams({ offset: offset + limit })}
            trailing={<ChevronRight className="h-4 w-4" aria-hidden="true" />}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
