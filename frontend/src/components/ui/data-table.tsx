import Link from "next/link";
import { ChevronsUpDown } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";

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
  items
}: {
  columns: Column<T>[];
  empty: ReactNode;
  getHref?: (item: T) => string;
  items: T[];
}) {
  if (items.length === 0) {
    return <>{empty}</>;
  }

  return (
    <div className="overflow-hidden rounded-[16px] border border-border bg-surface">
      <div className="overflow-x-auto">
        <table className="w-full min-w-full border-collapse text-left text-sm">
          <thead className="bg-bg-2/50 text-[10px] uppercase tracking-[0.14em] text-faint">
            <tr>
              {columns.map((column) => (
                <th
                  className={`border-b border-border px-4 py-3 font-semibold ${
                    column.align === "right" ? "text-right" : ""
                  }`}
                  style={column.width ? { width: column.width } : undefined}
                  key={column.key}
                >
                  {column.sortHref ? (
                    <Link
                      className="inline-flex items-center gap-1 transition hover:text-accent"
                      href={column.sortHref}
                    >
                      {column.header}
                      <ChevronsUpDown className="h-3 w-3" aria-hidden="true" />
                    </Link>
                  ) : (
                    column.header
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {items.map((item, rowIndex) => (
              <tr
                className="group row-reveal transition-colors duration-150 hover:bg-surface-2/60"
                style={{ "--i": rowIndex } as CSSProperties}
                key={item.id}
              >
                {columns.map((column, index) => {
                  const content = (
                    <>
                      <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-faint md:hidden">
                        {column.filterLabel ?? column.header}
                      </div>
                      <div className="mt-1 min-w-0 break-words md:mt-0">
                        {column.render(item)}
                      </div>
                    </>
                  );
                  return (
                    <td
                      className={`px-4 py-3.5 align-middle text-text ${
                        column.align === "right" ? "text-right" : ""
                      }`}
                      key={column.key}
                    >
                      {getHref ? (
                        <Link
                          className="block focus:outline-none"
                          href={getHref(item)}
                        >
                          {index === 0 && (
                            <span className="sr-only">Open record</span>
                          )}
                          {content}
                        </Link>
                      ) : (
                        content
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
