import { Table } from "mingli-web";

const columns = [
  { key: "subject", header: "档案", sortable: true },
  { key: "system", header: "体系" },
  { key: "created", header: "生成时间", sortable: true },
];

const rows = [
  { id: "R-1042", subject: "林某 · 本命", system: "八字", created: "2026-08-14 09:12" },
  { id: "R-1041", subject: "林某 · 流年", system: "八字", created: "2026-08-12 21:40" },
  { id: "R-1038", subject: "客户甲 · 择日", system: "六爻", created: "2026-08-09 15:03" },
  { id: "R-1035", subject: "客户乙 · 合参", system: "紫微", created: "2026-08-02 11:27" },
];

export function ReadingHistory() {
  return <Table caption="历史解读" columns={columns} rows={rows} />;
}

export function Filterable() {
  return (
    <Table
      caption="历史解读"
      columns={columns}
      rows={rows}
      filterLabel="筛选解读"
      filterPlaceholder="按档案或体系筛选"
    />
  );
}

export function SelectableWithPaging() {
  return (
    <Table
      caption="待归档解读"
      columns={columns}
      rows={rows}
      selectable
      pageSize={2}
      onSelectionChange={() => {}}
    />
  );
}

export function Empty() {
  return (
    <Table
      caption="历史解读"
      columns={columns}
      rows={[]}
      emptyState="还没有解读记录，完成第一次排盘后会显示在这里。"
    />
  );
}
