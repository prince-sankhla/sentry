import Link from "next/link";
import { ChevronsUpDown } from "lucide-react";
import type { ReactNode } from "react";

export type Column<T> = {
  key: string;
  header: string;
  align?: "left" | "right";
  render: (item: T) => ReactNode;
  sortHref?: string;
  filterLabel?: string;
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
    <div className="overflow-x-auto rounded-[6px] border border-[#2A3441] bg-[#121821]">
      <table className="w-full min-w-[780px] border-collapse text-left text-sm">
        <thead className="sticky top-0 z-10 bg-[#171F2A] text-[11px] uppercase tracking-[0.12em] text-[#9AA4AF]">
          <tr>
            {columns.map((column) => (
              <th className={`border-b border-[#2A3441] px-4 py-3 font-semibold ${column.align === "right" ? "text-right" : ""}`} key={column.key}>
                {column.sortHref ? (
                  <Link className="inline-flex items-center gap-1 hover:text-[#C58B2A]" href={column.sortHref}>
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
        <tbody className="divide-y divide-[#202A36]">
          {items.map((item) => {
            const row = (
              <>
                {columns.map((column) => (
                  <td className={`px-4 py-3 align-top text-[#E6E8EB] ${column.align === "right" ? "text-right" : ""}`} key={column.key}>
                    <div className="md:hidden text-[10px] font-semibold uppercase tracking-[0.12em] text-[#9AA4AF]">
                      {column.filterLabel ?? column.header}
                    </div>
                    <div className="mt-1 md:mt-0">{column.render(item)}</div>
                  </td>
                ))}
              </>
            );

            return getHref ? (
              <tr className="group bg-[#121821] transition hover:bg-[#171F2A]" key={item.id}>
                {columns.map((column, index) => (
                  <td className={`px-4 py-3 align-top text-[#E6E8EB] ${column.align === "right" ? "text-right" : ""}`} key={column.key}>
                    <Link className="block focus:outline-none" href={getHref(item)}>
                      {index === 0 ? (
                        <span className="sr-only">Open record</span>
                      ) : null}
                      <div className="md:hidden text-[10px] font-semibold uppercase tracking-[0.12em] text-[#9AA4AF]">
                        {column.filterLabel ?? column.header}
                      </div>
                      <div className="mt-1 md:mt-0">{column.render(item)}</div>
                    </Link>
                  </td>
                ))}
              </tr>
            ) : (
              <tr className="group bg-[#121821] transition hover:bg-[#171F2A]" key={item.id}>
                {row}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
