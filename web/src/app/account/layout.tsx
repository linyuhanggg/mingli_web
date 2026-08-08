import type { Metadata } from "next";
import type { ReactNode } from "react";

import { PrivateShell } from "@/components/private-shell";


export const metadata: Metadata = {
  title: "登录与账户",
  robots: { index: false, follow: false, nocache: true },
};

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";

export default function AccountLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <PrivateShell>{children}</PrivateShell>;
}
