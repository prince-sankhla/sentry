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
    <div className="overflow-hidden rounded-[20px] border border-[#E8D8B1] bg-white">
      <table className="w-full min-w-0 table-fixed border-collapse text-left text-sm">
        <thead className="sticky top-0 z-10 bg-[#FBF7F0] text-[11px] uppercase tracking-[0.12em] text-[#7A7F87]">
          <tr>
            {columns.map((column) => (
              <th className={`border-b border-[#F0E4C8] px-4 py-3 font-semibold ${column.align === "right" ? "text-right" : ""} min-w-0 break-words`} key={column.key}>
                {column.sortHref ? (
                  <Link className="inline-flex items-center gap-1 hover:text-[#B88927]" href={column.sortHref}>
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
        <tbody className="divide-y divide-[#F0E4C8]">
          {items.map((item) => {
            const row = (
              <>
                {columns.map((column) => (
                  <td className={`px-4 py-4 align-top text-[#2F2F2F] ${column.align === "right" ? "text-right" : ""} min-w-0 break-words`} key={column.key}>
                    <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#7A7F87] md:hidden">
                      {column.filterLabel ?? column.header}
                    </div>
                    <div className="mt-1 min-w-0 break-words md:mt-0">{column.render(item)}</div>
                  </td>
                ))}
              </>
            );

            return getHref ? (
              <tr className="group bg-white transition hover:bg-[#FCFAF5]" key={item.id}>
                {columns.map((column, index) => (
                  <td className={`px-4 py-4 align-top text-[#2F2F2F] ${column.align === "right" ? "text-right" : ""} min-w-0 break-words`} key={column.key}>
                    <Link className="block focus:outline-none" href={getHref(item)}>
                      {index === 0 ? (
                        <span className="sr-only">Open record</span>
                      ) : null}
                      <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#7A7F87] md:hidden">
                        {column.filterLabel ?? column.header}
                      </div>
                      <div className="mt-1 min-w-0 break-words md:mt-0">{column.render(item)}</div>
                    </Link>
                  </td>
                ))}
              </tr>
            ) : (
              <tr className="group bg-white transition hover:bg-[#FCFAF5]" key={item.id}>
                {row}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
