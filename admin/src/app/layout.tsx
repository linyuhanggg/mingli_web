import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "@fontsource-variable/noto-sans-sc";
import "@fontsource-variable/noto-serif-sc";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://admin.mingli.tools"),
  title: {
    default: "命理工具运营台",
    template: "%s｜命理工具运营台",
  },
  description: "员工内部运营后台。不面向公众。",
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: { index: false, follow: false, noimageindex: true },
  },
  applicationName: "命理工具运营台",
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
      <body>{children}</body>
    </html>
  );
}
