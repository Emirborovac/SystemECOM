"use client";

import type { ReactNode } from "react";
import { useMemo, useState } from "react";

export type DataTableColumn<T> = {
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
};

export function DataTable<T>({
  rows,
  columns,
  rowKey,
  filterPlaceholder,
  filterFn,
  pageSize = 50,
}: {
  rows: T[];
  columns: Array<DataTableColumn<T>>;
  rowKey: (row: T) => string;
  filterPlaceholder?: string;
  filterFn?: (row: T, q: string) => boolean;
  pageSize?: number;
}) {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    if (!filterFn || !q.trim()) return rows;
    const qq = q.trim().toLowerCase();
    return rows.filter((r) => filterFn(r, qq));
  }, [rows, q, filterFn]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, pageCount);
  const current = filtered.slice((safePage - 1) * pageSize, safePage * pageSize);

  return (
    <div>
      {filterFn ? (
        <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          <input
            className="input md:col-span-2"
            placeholder={filterPlaceholder || "Filter..."}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
          />
        </div>
      ) : null}

      <div className="overflow-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-border">
              {columns.map((c, idx) => (
                <th key={idx} className={`py-2 text-left ${c.className || ""}`.trim()}>
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {current.map((r) => (
              <tr key={rowKey(r)} className="border-b border-border">
                {columns.map((c, idx) => (
                  <td key={idx} className={`py-2 ${c.className || ""}`.trim()}>
                    {c.cell(r)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex items-center justify-between text-sm">
        <div className="text-muted">Results: {filtered.length}</div>
        <div className="flex items-center gap-2">
          <button className="btn btn-ghost" type="button" disabled={safePage <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
            Prev
          </button>
          <div className="text-muted">
            {safePage}/{pageCount}
          </div>
          <button
            className="btn btn-ghost"
            type="button"
            disabled={safePage >= pageCount}
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}


