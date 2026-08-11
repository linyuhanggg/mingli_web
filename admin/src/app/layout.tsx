import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "@fontsource-variable/noto-sans-sc";
import "@fontsource-variable/noto-serif-sc";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://admin.fateradar.cn"),
  title: {
    default: "FateRadar 运营台",
    template: "%s｜FateRadar 运营台",
  },
  description: "员工内部运营后台。不面向公众。",
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: { index: false, follow: false, noimageindex: true },
  },
  applicationName: "FateRadar Admin",
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
      <body>{children}</body>
    </html>
  );
}
