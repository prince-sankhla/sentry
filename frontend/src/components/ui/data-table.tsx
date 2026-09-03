import Link from "next/link";
import { ChevronsUpDown } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";

/**
 * Enterprise data table with optional row-level actions.
 *
 * Row actions live in a dedicated final cell rather than inside the record link,
 * so users can open the source record or launch an investigation without nested
 * interactive elements.
 */

export type Column<T> = {
  key: string;
  header: string;
  align?: "left" | "right";
  render: (item: T) => ReactNode;
  sortHref?: string;
  filterLabel?: string;
  width?: string;
};

export function DataTable<T extends { id: string }>({
  columns,
  empty,
  getHref,
  items,
  rowAction
}: {
  columns: Column<T>[];
  empty: ReactNode;
  getHref?: (item: T) => string;
  items: T[];
  rowAction?: (item: T) => ReactNode;
}) {
  if (items.length === 0) {
    return <>{empty}</>;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-surface elevate">
      <div className="overflow-x-auto">
        <table className="w-full min-w-full border-collapse text-left text-sm">
          <thead className="sticky top-0 z-10 bg-bg-2/95 backdrop-blur-sm">
            <tr>
              {columns.map((column) => (
                <th
                  className={`border-b border-border px-4 py-3.5 text-[10.5px] font-semibold uppercase tracking-[0.15em] text-faint ${
                    column.align === "right" ? "text-right" : ""
                  }`}
                  style={column.width ? { width: column.width } : undefined}
                  key={column.key}
                  scope="col"
                >
                  {column.sortHref ? (
                    <Link
                      className="group/sort inline-flex items-center gap-1.5 transition-colors duration-200 hover:text-accent"
                      href={column.sortHref}
                    >
                      {column.header}
                      <ChevronsUpDown
                        className="h-3 w-3 opacity-50 transition-opacity group-hover/sort:opacity-100 group-hover/sort:text-accent"
                        aria-hidden="true"
                      />
                    </Link>
                  ) : (
                    column.header
                  )}
                </th>
              ))}
              {rowAction ? (
                <th
                  className="w-[150px] border-b border-border px-4 py-3.5 text-right text-[10.5px] font-semibold uppercase tracking-[0.15em] text-faint"
                  scope="col"
                >
                  Action
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {items.map((item, rowIndex) => (
              <tr
                className="group row-reveal transition-colors duration-150 hover:bg-surface-2/50"
                style={{ "--i": rowIndex } as CSSProperties}
                key={item.id}
              >
                {columns.map((column, index) => {
                  const content = (
                    <>
                      <div className="t-label mb-1 md:hidden">
                        {column.filterLabel ?? column.header}
                      </div>
                      <div className="min-w-0 break-words">
                        {column.render(item)}
                      </div>
                    </>
                  );
                  return (
                    <td
                      className={`h-[52px] px-4 py-3.5 align-middle text-text ${
                        column.align === "right" ? "text-right" : ""
                      }`}
                      key={column.key}
                    >
                      {getHref ? (
                        <Link
                          className="block outline-none focus-visible:outline-2 focus-visible:outline-accent/75"
                          href={getHref(item)}
                        >
                          {index === 0 && <span className="sr-only">Open record</span>}
                          {content}
                        </Link>
                      ) : (
                        content
                      )}
                    </td>
                  );
                })}
                {rowAction ? (
                  <td className="px-4 py-3.5 text-right align-middle" onClick={(event) => event.stopPropagation()}>
                    {rowAction(item)}
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
