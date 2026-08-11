import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { RouteScrollPolicy } from "@/components/route-scroll-policy";

import "@fontsource-variable/noto-sans-sc";
import "@fontsource-variable/noto-serif-sc";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://fateradar.cn"),
  title: {
    default: "FateRadar｜个人命理档案与一事一问",
    template: "%s｜FateRadar",
  },
  description:
    "先做确定性计算，再给有依据、有边界、可核对的白话命理解读。",
  applicationName: "FateRadar",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  colorScheme: "light",
  themeColor: "#123a32",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <RouteScrollPolicy />
        {children}
      </body>
    </html>
  );
}
