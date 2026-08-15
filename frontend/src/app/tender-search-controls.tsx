"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useTransition } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import type { TenderSort } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { SearchInput, Select } from "@/components/ui/input";

type Props = {
  limit: number;
  offset: number;
  total: number;
  query: string;
  sort: TenderSort;
};

const sortOptions: { label: string; value: TenderSort }[] = [
  { label: "Newest", value: "newest" },
  { label: "Published date", value: "published_date" },
  { label: "Estimated value", value: "value" },
  { label: "Title", value: "title" }
];

export function TenderSearchControls({ limit, offset, total, query, sort }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const currentPage = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));
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
      <form className="grid gap-3 md:grid-cols-[1fr_180px_auto]" onSubmit={onSearch}>
        <label className="relative block">
          <span className="sr-only">Search tenders</span>
          <SearchInput
            defaultValue={query}
            name="q"
            placeholder="Search by title or procuring entity"
            type="search"
            pending={isPending}
          />
        </label>

        <label className="block">
          <span className="sr-only">Sort tenders</span>
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
        </label>

        <Button variant="primary" type="submit" disabled={isPending}>
          Search
        </Button>
      </form>

      <div className="mt-5 flex flex-col gap-3 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
        <div aria-live="polite">
          {isPending ? "Loading results..." : `Page ${currentPage} of ${pageCount}`}
        </div>
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
