import { notFound } from "next/navigation";

import { UiLab } from "@/components/ui-lab/ui-lab";

export default function UiLabPage() {
  if (process.env.NODE_ENV === "production") notFound();

  return <UiLab demoLabel="UI 演示数据" />;
}
