"use client";

import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import clsx from "clsx";

import styles from "./table.module.css";


export type SortDirection = "ascending" | "descending";

export type TableColumn = {
  key: string;
  header: string;
  sortable?: boolean;
};

export type TableRow = {
  id: string;
  [key: string]: unknown;
};

export type TableProps = {
  caption: string;
  columns: TableColumn[];
  rows: TableRow[];
  /** Provide an accessible text filter when set. */
  filterLabel?: string;
  filterPlaceholder?: string;
  /** Enable row selection with a select-all checkbox in the header. */
  selectable?: boolean;
  onSelectionChange?: (ids: string[]) => void;
  /** Enable pagination with this many rows per page. */
  pageSize?: number;
  /** Enable a per-row detail action that fires on activation. */
  onRowActivate?: (row: TableRow) => void;
  /** Accessible label for each row's detail action. */
  rowActionLabel?: string;
  /** Custom empty-state content (rendered when no rows are visible). */
  emptyState?: ReactNode;
};

function toText(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function compareValues(a: unknown, b: unknown): number {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return toText(a).localeCompare(toText(b), "zh-Hans-CN", { numeric: true });
}

export function Table({
  caption,
  columns,
  rows,
  filterLabel,
  filterPlaceholder,
  selectable = false,
  onSelectionChange,
  pageSize,
  onRowActivate,
  rowActionLabel = "查看详情",
  emptyState,
}: TableProps) {
  const filterId = useId();
  const [sort, setSort] = useState<{ key: string; direction: SortDirection } | null>(null);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [page, setPage] = useState(1);
  const selectAllRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(() => {
    const query = filter.trim().toLowerCase();
    if (!query) return rows;
    return rows.filter(
      (row) =>
        row.id.toLowerCase().includes(query) ||
        columns.some((column) => toText(row[column.key]).toLowerCase().includes(query)),
    );
  }, [rows, columns, filter]);

  const sorted = useMemo(() => {
    if (!sort) return filtered;
    const factor = sort.direction === "ascending" ? 1 : -1;
    return [...filtered].sort(
      (a, b) => factor * compareValues(a[sort.key], b[sort.key]),
    );
  }, [filtered, sort]);

  const totalPages =
    pageSize && pageSize > 0 ? Math.max(1, Math.ceil(sorted.length / pageSize)) : 1;
  const currentPage = Math.min(page, totalPages);
  const visibleRows =
    pageSize && pageSize > 0
      ? sorted.slice((currentPage - 1) * pageSize, currentPage * pageSize)
      : sorted;

  const allVisibleSelected =
    visibleRows.length > 0 && visibleRows.every((row) => selected.has(row.id));
  const someVisibleSelected = visibleRows.some((row) => selected.has(row.id));

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = someVisibleSelected && !allVisibleSelected;
    }
  }, [someVisibleSelected, allVisibleSelected]);

  function toggleSort(key: string) {
    setSort((previous) =>
      previous?.key === key
        ? { key, direction: previous.direction === "ascending" ? "descending" : "ascending" }
        : { key, direction: "ascending" },
    );
    setPage(1);
  }

  function toggleAll() {
    const next = new Set(selected);
    if (allVisibleSelected) {
      visibleRows.forEach((row) => next.delete(row.id));
    } else {
      visibleRows.forEach((row) => next.add(row.id));
    }
    setSelected(next);
    onSelectionChange?.(Array.from(next));
  }

  function toggleRow(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
    onSelectionChange?.(Array.from(next));
  }

  const colSpan = columns.length + (selectable ? 1 : 0) + (onRowActivate ? 1 : 0);

  return (
    <div className={styles.root} data-responsive-table="summary-rows">
      {filterLabel ? (
        <div className={styles.toolbar}>
          <label className={styles.filterLabel} htmlFor={filterId}>
            筛选
          </label>
          <input
            id={filterId}
            className={styles.filter}
            type="search"
            name="table-filter"
            autoComplete="off"
            aria-label={filterLabel}
            placeholder={filterPlaceholder}
            value={filter}
            onChange={(event) => {
              setFilter(event.target.value);
              setPage(1);
            }}
          />
        </div>
      ) : null}
      <div className={styles.scroller}>
        <table className={styles.table}>
          <caption className={styles.caption}>{caption}</caption>
          <thead>
            <tr>
              {selectable ? (
                <th className={clsx(styles.th, styles.thSelect)} scope="col">
                  <label className={styles.selectionTarget}>
                    <input
                      ref={selectAllRef}
                      className={styles.checkbox}
                      type="checkbox"
                      aria-label="全选"
                      checked={allVisibleSelected}
                      onChange={toggleAll}
                      disabled={visibleRows.length === 0}
                    />
                  </label>
                </th>
              ) : null}
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={styles.th}
                  scope="col"
                  aria-sort={
                    column.sortable
                      ? sort?.key === column.key
                        ? sort.direction
                        : "none"
                      : undefined
                  }
                >
                  {column.sortable ? (
                    <button
                      type="button"
                      className={styles.sortButton}
                      onClick={() => toggleSort(column.key)}
                    >
                      {column.header}
                    </button>
                  ) : (
                    column.header
                  )}
                </th>
              ))}
              {onRowActivate ? (
                <th className={clsx(styles.th, styles.thAction)} scope="col">
                  <span className="sr-only">操作</span>
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {visibleRows.length === 0 ? (
              <tr>
                <td className={styles.empty} colSpan={colSpan}>
                  {emptyState ?? "暂无数据"}
                </td>
              </tr>
            ) : (
              visibleRows.map((row) => (
                <tr key={row.id}>
                  {selectable ? (
                    <td className={styles.td} data-selection-cell="true">
                      <label className={styles.selectionTarget}>
                        <input
                          className={styles.checkbox}
                          type="checkbox"
                          aria-label={`选择 ${toText(row.id)}`}
                          checked={selected.has(row.id)}
                          onChange={() => toggleRow(row.id)}
                        />
                      </label>
                    </td>
                  ) : null}
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={styles.td}
                      data-column-key={column.key}
                      data-label={column.header}
                    >
                      {row[column.key] as ReactNode}
                    </td>
                  ))}
                  {onRowActivate ? (
                    <td className={styles.td} data-action-cell="true">
                      <button
                        type="button"
                        className={styles.detailButton}
                        aria-label={`${rowActionLabel} ${toText(row.id)}`}
                        onClick={() => onRowActivate(row)}
                      >
                        {rowActionLabel}
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {pageSize ? (
        <nav className={styles.pagination} aria-label="分页">
          <button
            type="button"
            className={styles.pageButton}
            onClick={() => setPage(currentPage - 1)}
            disabled={currentPage <= 1}
            aria-label="上一页"
          >
            上一页
          </button>
          <span className={styles.pageInfo}>
            第 {currentPage} / {totalPages} 页
          </span>
          <button
            type="button"
            className={styles.pageButton}
            onClick={() => setPage(currentPage + 1)}
            disabled={currentPage >= totalPages}
            aria-label="下一页"
          >
            下一页
          </button>
        </nav>
      ) : null}
    </div>
  );
}
