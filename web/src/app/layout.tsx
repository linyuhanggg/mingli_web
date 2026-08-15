import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { AccountSessionProvider } from "@/components/account-session-context";
import { RouteScrollPolicy } from "@/components/route-scroll-policy";
import { ServiceWorkerRegistration } from "@/components/service-worker-registration";

import "@fontsource-variable/noto-sans-sc";
import "@fontsource-variable/noto-serif-sc";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "命理工具｜可核对的盘面与解读",
    template: "%s｜命理工具",
  },
  description:
    "先做确定性计算，再给有依据、有边界、可核对的白话命理解读。",
  applicationName: "命理工具",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  colorScheme: "light",
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <AccountSessionProvider>
          <RouteScrollPolicy />
          <ServiceWorkerRegistration />
          {children}
        </AccountSessionProvider>
      </body>
    </html>
  );
}
