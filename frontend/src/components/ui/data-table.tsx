import Link from "next/link";
import { ChevronsLeftRight, ChevronsUpDown } from "lucide-react";
import type { ReactNode } from "react";

export type Column<T> = {
  key: string;
  header: string;
  align?: "left" | "right";
  render: (item: T) => ReactNode;
  sortHref?: string;
  filterLabel?: string;
  sortValue?: (item: T) => string | number | null | undefined;
};

export function DataTable<T extends { id: string }>({
  columns,
  empty,
  getHref,
  onRowSelect,
  selectedId,
  sortState,
  onSortChange,
  items
}: {
  columns: Column<T>[];
  empty: ReactNode;
  getHref?: (item: T) => string;
  onRowSelect?: (item: T) => void;
  selectedId?: string | null;
  sortState?: { key: string; direction: "asc" | "desc" };
  onSortChange?: (column: Column<T>) => void;
  items: T[];
}) {
  const visibleItems = sortState ? sortItems(items, columns, sortState) : items;

  if (visibleItems.length === 0) {
    return <>{empty}</>;
  }

  return (
    <div className="sentry-scrollbar overflow-x-auto rounded-[4px] border border-[#2A2A2A] bg-[#111111]">
      <table className="w-full min-w-[860px] table-fixed border-collapse text-left text-sm">
        <thead className="sticky top-0 z-10 bg-[#181818] text-[11px] uppercase tracking-[0.12em] text-[#737373]">
          <tr>
            {columns.map((column) => (
              <th className={`border-b border-[#2A2A2A] px-4 py-3 font-semibold ${column.align === "right" ? "text-right" : ""}`} key={column.key}>
                {onSortChange && column.sortValue ? (
                  <button className="inline-flex items-center gap-1 hover:text-[#F7F7F7]" onClick={() => onSortChange(column)} type="button">
                    {column.header}
                    {sortState?.key === column.key ? (
                      sortState.direction === "asc" ? <ChevronsUpDown className="h-3 w-3 rotate-180" aria-hidden="true" /> : <ChevronsUpDown className="h-3 w-3" aria-hidden="true" />
                    ) : (
                      <ChevronsLeftRight className="h-3 w-3" aria-hidden="true" />
                    )}
                  </button>
                ) : column.sortHref ? (
                  <Link className="inline-flex items-center gap-1 hover:text-[#F7F7F7]" href={column.sortHref}>
                    {column.header}
                    <ChevronsUpDown className="h-3 w-3" aria-hidden="true" />
                  </Link>
                ) : (
                  <span className="inline-flex items-center gap-1">
                    {column.header}
                    <ChevronsLeftRight className="h-3 w-3 text-[#3A3A3A]" aria-hidden="true" />
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#242424]">
          {visibleItems.map((item) => {
            const row = (
              <>
                {columns.map((column) => (
                  <td className={`px-4 py-3 align-top text-[#F7F7F7] ${column.align === "right" ? "text-right" : ""}`} key={column.key}>
                    <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#737373] md:hidden">
                      {column.filterLabel ?? column.header}
                    </div>
                    <div className="mt-1 md:mt-0">{column.render(item)}</div>
                  </td>
                ))}
              </>
            );

            const rowClassName = `group bg-[#111111] transition duration-150 ease-out hover:bg-[#181818] ${selectedId === item.id ? "bg-[#181818] ring-1 ring-inset ring-[#C58B2A]" : ""} ${onRowSelect ? "cursor-pointer" : ""}`;

            return getHref ? (
              <tr className={rowClassName} key={item.id}>
                {columns.map((column, index) => (
                  <td className={`px-4 py-3 align-top text-[#F7F7F7] ${column.align === "right" ? "text-right" : ""}`} key={column.key}>
                    <Link className="block focus:outline-none" href={getHref(item)}>
                      {index === 0 ? (
                        <span className="sr-only">Open record</span>
                      ) : null}
                      <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#737373] md:hidden">
                        {column.filterLabel ?? column.header}
                      </div>
                      <div className="mt-1 md:mt-0">{column.render(item)}</div>
                    </Link>
                  </td>
                ))}
              </tr>
            ) : onRowSelect ? (
              <tr
                className={rowClassName}
                key={item.id}
                data-selected={selectedId === item.id ? "true" : "false"}
                onClick={() => onRowSelect(item)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onRowSelect(item);
                  }
                }}
                tabIndex={0}
              >
                {row}
              </tr>
            ) : (
              <tr className={rowClassName} key={item.id}>
                {row}
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="flex items-center justify-between border-t border-[#2A2A2A] bg-[#111111] px-4 py-2 text-xs text-[#737373]">
        <span>{visibleItems.length} visible rows</span>
        <span>Filter, sort, and open rows for investigation context</span>
      </div>
    </div>
  );
}

function sortItems<T>(items: T[], columns: Column<T>[], sortState: { key: string; direction: "asc" | "desc" }): T[] {
  const column = columns.find((candidate) => candidate.key === sortState.key);
  if (!column?.sortValue) return items;

  const direction = sortState.direction === "asc" ? 1 : -1;
  return [...items].sort((left, right) => {
    const leftValue = normalizeSortValue(column.sortValue?.(left));
    const rightValue = normalizeSortValue(column.sortValue?.(right));

    if (leftValue === rightValue) return 0;
    if (leftValue === null) return 1;
    if (rightValue === null) return -1;
    return leftValue > rightValue ? direction : -direction;
  });
}

function normalizeSortValue(value: string | number | null | undefined): string | number | null {
  if (value === undefined || value === null) return null;
  return typeof value === "string" ? value.toLowerCase() : value;
}
